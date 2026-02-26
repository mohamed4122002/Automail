# Campaign Execution System - Setup & Verification Guide

## 🎯 Quick Start

### Option 1: Using Docker Compose (Recommended)

```powershell
# Windows
.\scripts\start-dev.ps1

# Linux/Mac
chmod +x scripts/start-dev.sh
./scripts/start-dev.sh
```

This will start:
- PostgreSQL database
- Redis
- Backend API
- Celery Worker
- Celery Beat (scheduler)

### Option 2: Manual Setup

**Terminal 1 - Backend API:**
```bash
cd backend
uvicorn backend.main:app --reload
```

**Terminal 2 - Celery Worker:**
```bash
cd backend
celery -A backend.celery_app worker --loglevel=info --pool=solo
```

**Terminal 3 - Celery Beat:**
```bash
cd backend
celery -A backend.celery_app beat --loglevel=info
```

**Terminal 4 - Frontend:**
```bash
cd frontend
npm run dev
```

---

## ✅ Verification

### 1. Run Automated Verification Script

```bash
cd backend
python -m backend.scripts.verify_system
```

This checks:
- ✓ Database connectivity
- ✓ Redis connectivity
- ✓ Celery workers running
- ✓ Test data availability
- ✓ Campaign activation flow

### 2. Check System Health via API

```bash
# Check overall system health
curl http://localhost:8000/api/system/health

# Check worker status
curl http://localhost:8000/api/system/workers

# Check task statistics
curl http://localhost:8000/api/system/tasks/stats
```

### 3. Check Worker Status in UI

1. Navigate to http://localhost:5173
2. Login with your credentials
3. Go to Dashboard
4. Look for the **Worker Status Indicator** at the top
   - 🟢 Green = Workers active
   - 🟡 Amber = No workers (tasks will queue)

---

## 🐛 Troubleshooting

### Issue: "No Celery workers detected"

**Solution:**
```bash
# Check if workers are running
docker-compose ps

# If not, start them
docker-compose up -d worker beat

# View worker logs
docker-compose logs -f worker
```

### Issue: "Campaign activated but no emails sent"

**Checklist:**
1. ✓ Celery workers running? (Check worker status indicator)
2. ✓ Campaign has contact list assigned?
3. ✓ Contact list has contacts?
4. ✓ Workflow linked to campaign?
5. ✓ Workflow has email nodes?
6. ✓ Email templates exist?

**Debug:**
```bash
# Check workflow instances created
docker-compose exec backend python -c "
from backend.db import AsyncSessionLocal
from backend.models import WorkflowInstance
from sqlalchemy import select
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(WorkflowInstance))
        instances = result.scalars().all()
        print(f'Workflow instances: {len(instances)}')
        for i in instances:
            print(f'  - {i.id}: status={i.status}')

asyncio.run(check())
"
```

### Issue: "Tasks queued but not executing"

**Cause:** Celery worker not running

**Solution:**
```bash
# Start worker
docker-compose up -d worker

# Or manually
celery -A backend.celery_app worker --loglevel=info --pool=solo
```

---

## 📊 Monitoring

### View Celery Worker Logs
```bash
docker-compose logs -f worker
```

### View Backend API Logs
```bash
docker-compose logs -f backend
```

### View All Service Status
```bash
docker-compose ps
```

---

## 🔧 Useful Commands

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart worker
docker-compose restart backend
```

### Stop All Services
```bash
docker-compose down
```

### View Database
```bash
docker-compose exec db psql -U automation_user -d marketing_automation
```

### Clear Redis
```bash
docker-compose exec redis redis-cli FLUSHALL
```

---

## 📝 What Was Fixed

### 1. **Critical Bug in `campaign_manager.py`**
   - **Issue:** Line 110 attempted to add `None` to database
   - **Fix:** Properly instantiate `WorkflowInstance` object before adding

### 2. **Missing Celery Beat Scheduler**
   - **Issue:** Periodic tasks (warmup, retries) not running
   - **Fix:** Added `beat` service to `docker-compose.yml`

### 3. **No System Health Monitoring**
   - **Issue:** No visibility into worker status
   - **Fix:** Created `/api/system/health`, `/api/system/workers`, `/api/system/tasks/stats` endpoints

### 4. **Poor Error Feedback**
   - **Issue:** Campaign activation failed silently
   - **Fix:** Enhanced activation endpoint with worker status warnings

---

## 🎉 Success Indicators

When everything is working correctly, you should see:

1. **In Dashboard UI:**
   - 🟢 Green worker status indicator showing "X Workers Active"

2. **In Worker Logs:**
   ```
   [INFO] Queuing workflow task for new instance <uuid>
   [INFO] Task advance_workflow_task[<uuid>] received
   [INFO] Task send_email_task[<uuid>] received
   ```

3. **In Console (Email Provider):**
   ```
   ========================================
   📧 EMAIL SENT (Console Provider)
   ========================================
   To: user@example.com
   Subject: Your Subject
   ```

4. **In Database:**
   ```sql
   SELECT COUNT(*) FROM workflow_instances WHERE status = 'running';
   -- Should return > 0
   ```

---

## 📞 Need Help?

If you're still experiencing issues:

1. Run the verification script: `python -m backend.scripts.verify_system`
2. Check the logs: `docker-compose logs -f`
3. Verify all services are running: `docker-compose ps`
4. Check system health: `curl http://localhost:8000/api/system/health`
