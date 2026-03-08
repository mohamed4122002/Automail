import json
from redis import Redis
from datetime import datetime
from uuid import UUID
from typing import Dict, Any, Optional
from ..models import Campaign
from ..config import settings

class ReputationWarmupService:
    def __init__(self, redis_client: Optional[Redis] = None):
        # Initialize Redis client if not provided
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    def _get_daily_key(self, campaign_id: UUID | str) -> str:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return f"warmup:{str(campaign_id)}:{today}"

    async def check_warmup_limit(self, campaign_id: UUID | str) -> bool:
        """Returns True if within limit, False if limit reached."""
        campaign = await Campaign.find_one(Campaign.id == (UUID(campaign_id) if isinstance(campaign_id, str) else campaign_id))
        
        if not campaign or not campaign.warmup_config.get("enabled"):
            return True

        current_limit = campaign.warmup_config.get("current_limit", 10)
        daily_key = self._get_daily_key(campaign_id)
        
        sent_today = int(self.redis.get(daily_key) or 0)
        return sent_today < current_limit

    async def increment_sent_count(self, campaign_id: UUID | str):
        daily_key = self._get_daily_key(campaign_id)
        self.redis.incr(daily_key)
        # Set expiry to 48h to ensure it clears but stays long enough for edge cases
        self.redis.expire(daily_key, 172800)

    async def get_warmup_status(self, campaign_id: UUID | str) -> Dict[str, Any]:
        campaign = await Campaign.find_one(Campaign.id == (UUID(campaign_id) if isinstance(campaign_id, str) else campaign_id))
        if not campaign:
            return {}

        daily_key = self._get_daily_key(campaign_id)
        sent_today = int(self.redis.get(daily_key) or 0)
        
        return {
            "enabled": campaign.warmup_config.get("enabled", False),
            "current_limit": campaign.warmup_config.get("current_limit", 0),
            "sent_today": sent_today,
            "max_volume": campaign.warmup_config.get("max_volume", 0),
            "progress_pct": round((sent_today / campaign.warmup_config.get("current_limit", 1) * 100), 1) if campaign.warmup_config.get("enabled") else 0
        }

    async def process_daily_increase(self):
        """Task to increment volume for all active warmup campaigns."""
        campaigns = await Campaign.find(Campaign.is_active == True).to_list()
        
        count = 0
        for campaign in campaigns:
            cfg = campaign.warmup_config
            if not cfg.get("enabled"):
                continue
            
            # Check if already increased today
            today = datetime.utcnow().date()
            if campaign.warmup_last_limit_increase and campaign.warmup_last_limit_increase.date() >= today:
                continue

            current_limit = cfg.get("current_limit", 10)
            increase_pct = cfg.get("daily_increase_pct", 10.0)
            max_vol = cfg.get("max_volume", 1000)
            
            if current_limit < max_vol:
                new_limit = int(current_limit * (1 + (increase_pct / 100)))
                # If int conversion didn't increase it (e.g. 10 * 1.05 = 10.5 -> 10), force +1
                if new_limit == current_limit:
                    new_limit += 1
                
                new_limit = min(new_limit, max_vol)
                
                # Update DB
                new_cfg = dict(cfg)
                new_cfg["current_limit"] = new_limit
                campaign.warmup_config = new_cfg
                campaign.warmup_last_limit_increase = datetime.utcnow()
                await campaign.save()
                count += 1
        
        return count
