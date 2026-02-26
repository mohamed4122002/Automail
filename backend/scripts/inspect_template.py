import sys
import os
from uuid import UUID
from sqlalchemy import select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core.db import task_context
from backend.models import EmailTemplate

async def inspect_template(template_id_str):
    template_id = UUID(template_id_str)
    async with task_context() as db:
        res = await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))
        tmpl = res.scalar_one_or_none()
        if not tmpl:
            print(f"[ERROR] Template {template_id_str} not found")
            return
        print(f"[OK] Template: {tmpl.name}")
        print(f"[SUBJECT] Subject: {tmpl.subject}")
        print("--- HTML BODY ---")
        print(tmpl.html_body)
        print("-----------------")

if __name__ == "__main__":
    from backend.core.async_runner import run_async
    tid = "0b3f123e-81a5-4cdb-a887-d6849ea9cbe4"
    if len(sys.argv) > 1:
        tid = sys.argv[1]
    run_async(inspect_template(tid))
