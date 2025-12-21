import asyncio
import os
from contextlib import suppress
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Block, Form, User
from app.utils.email_client import send_email

URGENT_MINUTES = int(os.getenv("REMINDER_URGENT_MINUTES", "5"))
NORMAL_HOURS = int(os.getenv("REMINDER_NORMAL_HOURS", "48"))
CHECK_INTERVAL_SECONDS = int(os.getenv("REMINDER_CHECK_INTERVAL_SECONDS", "60"))


def _fetch_due_blocks(db: Session):
    now = datetime.utcnow()
    urgent_deadline = now - timedelta(minutes=URGENT_MINUTES)
    normal_deadline = now - timedelta(hours=NORMAL_HOURS)

    return (
        db.query(Block)
        .filter(
            Block.reminder_sent == 0,
            (
                (Block.status == "urgent") & (Block.last_message_at <= urgent_deadline)
            )
            | (
                (Block.status == "normal") & (Block.last_message_at <= normal_deadline)
            ),
        )
        .all()
    )


def _collect_recipients(db: Session, form: Form) -> list[str]:
    recipients: list[str] = []
    client = db.get(User, form.user_id)
    if client and client.email:
        recipients.append(client.email)
    if form.developer_id:
        developer = db.get(User, form.developer_id)
        if developer and developer.email:
            recipients.append(developer.email)
    # remove duplicates while preserving order
    unique: list[str] = []
    for email in recipients:
        if email not in unique:
            unique.append(email)
    return unique


def _format_email(block: Block, form: Form) -> tuple[str, str]:
    subject = f"[SyncBridge] {block.status.title()} reminder for form {form.id}"
    last_ts = block.last_message_at.strftime("%Y-%m-%d %H:%M:%S UTC") if block.last_message_at else "unknown"
    html = (
        f"<p>Form: {form.title}</p>"
        f"<p>Status: {block.status}</p>"
        f"<p>Block type: {block.type}</p>"
        f"<p>Last message at: {last_ts}</p>"
        f"<p>This is an automated reminder from bridge-no-reply@icu.584743.xyz.</p>"
    )
    return subject, html


def process_due_blocks_once(db: Session) -> None:
    due_blocks = _fetch_due_blocks(db)
    for block in due_blocks:
        form = db.get(Form, block.form_id)
        if not form:
            block.reminder_sent = 1
            db.add(block)
            db.commit()
            continue
        recipients = _collect_recipients(db, form)
        if not recipients:
            block.reminder_sent = 1
            db.add(block)
            db.commit()
            continue
        subject, html = _format_email(block, form)
        try:
            send_email(recipients, subject, html)
            block.reminder_sent = 1
            db.add(block)
            db.commit()
        except Exception:
            # Keep reminder_sent as is to retry next cycle
            db.rollback()


async def start_reminder_loop():
    while True:
        try:
            db = SessionLocal()
            try:
                process_due_blocks_once(db)
            finally:
                db.close()
        except Exception:
            # swallow to keep loop alive
            pass
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def stop_task(task: asyncio.Task | None):
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            asyncio.get_event_loop().run_until_complete(task)
