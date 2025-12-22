from sqlalchemy.orm import Session

from app.models import File


def get_by_id(db: Session, file_id: int) -> File | None:
    return db.query(File).filter(File.id == file_id).first()


def create_record(
    db: Session,
    message_id: int,
    filename: str,
    file_type: str,
    file_size: int,
    storage_path: str,
    file_ext: str,
) -> File:
    rec = File(
        message_id=message_id,
        file_name=filename,
        file_type=file_type,
        file_size=file_size,
        file_ext=file_ext,
        storage_path=storage_path,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def delete_record(db: Session, rec: File):
    db.delete(rec)
    db.commit()


def list_by_message(db: Session, message_id: int) -> list[File]:
    return db.query(File).filter(File.message_id == message_id).all()
