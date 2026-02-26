import re
from typing import List, Dict, Any

class SpamShieldService:
    """Service to detect spam trigger words and patterns in email content and subjects."""

    # Common spam trigger words categorized by risk
    HIGH_RISK_WORDS = [
        "free", "win", "winner", "prize", "cash", "money", "guaranteed",
        "urgent", "congratulations", "act now", "apply now", "debt",
        "risk-free", "investment", "bitcoin", "crypto", "bonus",
        "unlimited", "save big", "billion", "million", "payroll",
        "verify", "password", "account suspended", "legal notice"
    ]

    MEDIUM_RISK_WORDS = [
        "click here", "limited time", "offer", "discount", "lowest price",
        "mortgage", "finance", "medicine", "viagra", "pills", "weight loss"
    ]

    # Regex patterns for common spam formatting
    SPAM_PATTERNS = [
        (r'!!{2,}', "Excessive exclamation marks"),
        (r'\${3,}', "Excessive dollar signs"),
        (r'[A-Z\s]{10,}', "Excessive capitalization"),
        (r'f\.r\.e\.e', "Obfuscated keywords"),
    ]

    def __init__(self):
        # Compile patterns for efficiency
        self.compiled_patterns = [(re.compile(p, re.IGNORECASE), desc) for p, desc in self.SPAM_PATTERNS]

    def check_text(self, text: str) -> Dict[str, Any]:
        """Analyzes text and returns a spam risk report."""
        if not text:
            return {"is_spam": False, "score": 0.0, "triggers": []}

        triggers = []
        score = 0.0
        text_lower = text.lower()

        # Check high risk words
        for word in self.HIGH_RISK_WORDS:
            if re.search(rf'\b{re.escape(word)}\b', text_lower):
                triggers.append(f"High risk word: '{word}'")
                score += 0.3

        # Check medium risk words
        for word in self.MEDIUM_RISK_WORDS:
            if re.search(rf'\b{re.escape(word)}\b', text_lower):
                triggers.append(f"Medium risk word: '{word}'")
                score += 0.15

        # Check patterns
        for pattern, desc in self.compiled_patterns:
            if pattern.search(text):
                triggers.append(desc)
                score += 0.2

        # Normalize score
        score = min(score, 1.0)
        
        return {
            "is_spam": score > 0.6,
            "score": round(score, 2),
            "triggers": triggers
        }

# Global singleton
spam_shield_service = SpamShieldService()
