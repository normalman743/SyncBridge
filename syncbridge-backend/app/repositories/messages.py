from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Message


def get_by_id(db: Session, message_id: int) -> Message | None:
    return db.query(Message).filter(Message.id == message_id).first()


def list_messages(db: Session, block_id: int, page: int, page_size: int):
    # latest-first feed so page 1 shows most recent messages
    query = db.query(Message).filter(Message.block_id == block_id).order_by(Message.created_at.desc())
    total = query.count()
    items = (
        query.offset(max(page - 1, 0) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def create_message(db: Session, block_id: int, user_id: int, text: str) -> Message:
    msg = Message(
        block_id=block_id,
        user_id=user_id,
        text_content=text,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def update_message(db: Session, msg: Message, changes: dict) -> Message:
    allowed_fields = {"text_content"}
    for field, value in changes.items():
        if field in allowed_fields and hasattr(msg, field):
            setattr(msg, field, value)
    msg.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)
    return msg


def delete_message(db: Session, msg: Message):
    db.delete(msg)
    db.commit()
