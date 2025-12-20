# app/routers/files.py
import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models import File as FileModel, Message, User
from app.repositories import files as file_repo
from app.repositories import messages as message_repo
from app.services.permissions import assert_can_delete_file, assert_can_upload_file, get_current_user
from app.utils import error, success

load_dotenv()
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default

# upload dir inside app folder
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(HERE, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter()

@router.post("/file")
def upload_file(message_id: int, file: UploadFile = File(...), current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = message_repo.get_by_id(db, message_id)
    if not m:
        raise HTTPException(status_code=404, detail=error("Message not found", "NOT_FOUND"))
    # permission + block/form access
    assert_can_upload_file(m, current, db)
    # read in chunks to avoid memory blow-up (but here simple)
    contents = file.file.read()
    size = len(contents)
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=error("File too large", "VALIDATION_ERROR"))
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(contents)
    rec = file_repo.create_record(db, message_id, file.filename, file.content_type or "", size, path)
    return success({"file_id": rec.id}, "File uploaded")

@router.get("/file/{id}")
def get_file(id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rec = file_repo.get_by_id(db, id)
    if not rec:
        raise HTTPException(status_code=404, detail=error("Not found", "NOT_FOUND"))
    # check permission: ensure requester can access the message's block/form
    m = message_repo.get_by_id(db, rec.message_id)
    if not m:
        raise HTTPException(status_code=404, detail=error("Message not found", "NOT_FOUND"))
    assert_can_upload_file(m, current, db)
    # return metadata (frontend can fetch path or backend can serve file route)
    return success({"id": rec.id, "file_name": rec.file_name, "file_size": rec.file_size, "storage_path": rec.storage_path})

@router.delete("/file/{id}")
def delete_file(id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rec = file_repo.get_by_id(db, id)
    if not rec:
        raise HTTPException(status_code=404, detail=error("Not found", "NOT_FOUND"))
    assert_can_delete_file(rec, current, db)
    # delete file from disk if exists
    try:
        if rec.storage_path and os.path.exists(rec.storage_path):
            os.remove(rec.storage_path)
    except Exception:
        pass
    file_repo.delete_record(db, rec)
    return success(None, "File deleted")
