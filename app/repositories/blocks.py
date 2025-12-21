from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Block


def get_by_id(db: Session, block_id: int) -> Block | None:
    return db.query(Block).filter(Block.id == block_id).first()


def get_or_create(db: Session, form_id: int, function_id: int | None = None, nonfunction_id: int | None = None) -> Block:
    block_type = "general"
    target_id = None
    if function_id:
        block_type = "function"
        target_id = function_id
    elif nonfunction_id:
        block_type = "nonfunction"
        target_id = nonfunction_id

    block = (
        db.query(Block)
        .filter(Block.form_id == form_id, Block.type == block_type, Block.target_id == target_id)
        .first()
    )
    if block:
        return block

    now = datetime.utcnow()
    block = Block(
        form_id=form_id,
        type=block_type,
        target_id=target_id,
        status="normal",
        created_at=now,
        last_message_at=now,
        reminder_sent=0,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


def touch_activity(db: Session, block: Block) -> Block:
    block.last_message_at = datetime.utcnow()
    block.reminder_sent = 0
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


def update_status(db: Session, block: Block, status: str) -> Block:
    block.status = status
    block.reminder_sent = 0
    block.last_message_at = datetime.utcnow()
    db.add(block)
    db.commit()
    db.refresh(block)
    return block
