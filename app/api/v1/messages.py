# app/routers/messages.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models import Block, Message, User
from app.repositories import blocks as block_repo
from app.repositories import files as file_repo
from app.repositories import forms as form_repo
from app.repositories import messages as message_repo
from app.schemas import MessageIn, MessageUpdate
from app.services.audit import log_audit
from app.services.permissions import assert_can_access_block, assert_can_edit_message, assert_can_post_message, get_current_user
from app.services.websocket_manager import manager
from app.utils import error, success

router = APIRouter()


# ============================================================
# Helper: build consistent WS room key
# ============================================================
def _make_room_key(form_id: int, function_id: Optional[int], nonfunction_id: Optional[int]):
    if function_id:
        return f"form:{form_id}:function:{function_id}"
    if nonfunction_id:
        return f"form:{form_id}:nonfunction:{nonfunction_id}"
    return f"form:{form_id}:general"


# ============================================================
# GET messages
# ============================================================
@router.get("/messages")
def get_messages(
    form_id: int,
    function_id: int = None,
    nonfunction_id: int = None,
    page: int = 1,
    page_size: int = 20,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = form_repo.get(db, form_id)
    if not form:
        raise HTTPException(status_code=404, detail=error("Form not found", "NOT_FOUND"))

    assert_can_access_block(form, current, db)

    block = block_repo.get_or_create(db, form_id, function_id, nonfunction_id)
    items, total = message_repo.list_messages(db, block.id, page, page_size)

    out = []
    for m in items:
        attachments = file_repo.list_by_message(db, m.id)
        out.append(
            {
                "id": m.id,
                "block_id": m.block_id,
                "user_id": m.user_id,
                "text_content": m.text_content,
                "created_at": str(m.created_at),
                "files": [
                    {
                        "id": f.id,
                        "file_name": f.file_name,
                        "file_size": f.file_size,
                    }
                    for f in attachments
                ],
            }
        )

    return success(
        {"messages": out, "page": page, "page_size": page_size, "total": total}
    )


# ============================================================
# POST message
# (Here we add WebSocket broadcast)
# ============================================================
@router.post("/message")
async def post_message(
    payload: MessageIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = form_repo.get(db, payload.form_id)
    if not form:
        raise HTTPException(status_code=404, detail=error("Form not found", "NOT_FOUND"))

    # Check access
    assert_can_access_block(form, current, db)
    assert_can_post_message(form, current)

    # Create / get block
    block = block_repo.get_or_create(
        db, payload.form_id, payload.function_id, payload.nonfunction_id
    )

    msg = message_repo.create_message(db, block.id, current.id, payload.text_content)

    # Track activity time for reminder checks
    block_repo.touch_activity(db, block)

    # ========== WebSocket Broadcast ==========
    room = _make_room_key(payload.form_id, payload.function_id, payload.nonfunction_id)

    await manager.broadcast(
        room,
        {
            "type": "message",
            "action": "create",
            "message": {
                "id": msg.id,
                "block_id": msg.block_id,
                "user_id": msg.user_id,
                "text_content": msg.text_content,
                "created_at": str(msg.created_at),
            },
        },
    )
    # =========================================

    return success({"message_id": msg.id}, "Message sent")


# ============================================================
# UPDATE block status (normal/urgent)
# ============================================================
@router.put("/block/{id}/status")
def update_block_status(
    id: int,
    body: dict,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    status = body.get("status") if body else None
    if status not in ("normal", "urgent"):
        raise HTTPException(status_code=400, detail=error("Invalid status", "VALIDATION_ERROR"))

    block = block_repo.get_by_id(db, id)
    if not block:
        raise HTTPException(status_code=404, detail=error("Block not found", "NOT_FOUND"))

    form = form_repo.get(db, block.form_id)
    if not form:
        raise HTTPException(status_code=404, detail=error("Form not found", "NOT_FOUND"))

    assert_can_access_block(form, current, db)

    block_repo.update_status(db, block, status)
    return success(None, "Block status updated")


# ============================================================
# UPDATE message
# (Also broadcast update)
# ============================================================
@router.put("/message/{id}")
async def update_message(
    id: int,
    payload: MessageUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = message_repo.get_by_id(db, id)
    if not msg:
        raise HTTPException(status_code=404, detail=error("Message not found", "NOT_FOUND"))

    assert_can_edit_message(msg, current)

    changes = payload.dict(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail=error("No valid fields to update", "VALIDATION_ERROR"))

    message_repo.update_message(db, msg, changes)

    # WS broadcast updated content
    block = block_repo.get_by_id(db, msg.block_id)
    room = _make_room_key(block.form_id, block.target_id if block.type == "function" else None,
                          block.target_id if block.type == "nonfunction" else None)

    await manager.broadcast(
        room,
        {
            "type": "message",
            "action": "update",
            "message": {
                "id": msg.id,
                "block_id": msg.block_id,
                "user_id": msg.user_id,
                "text_content": msg.text_content,
                "updated_at": str(msg.updated_at),
            },
        },
    )

    return success(None, "Message updated")


# ============================================================
# DELETE message
# (Also broadcast delete)
# ============================================================
@router.delete("/message/{id}")
async def delete_message(
    id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = message_repo.get_by_id(db, id)
    if not msg:
        raise HTTPException(status_code=404, detail=error("Message not found", "NOT_FOUND"))

    assert_can_edit_message(msg, current)

    # Get block info before deletion
    block = block_repo.get_by_id(db, msg.block_id)
    room = _make_room_key(block.form_id, block.target_id if block.type == "function" else None,
                          block.target_id if block.type == "nonfunction" else None)

    # Audit log before deletion
    log_audit(db, "message", msg.id, "delete", current.id, {"text_content": msg.text_content[:100], "block_id": msg.block_id}, None)

    message_repo.delete_message(db, msg)

    # WS broadcast delete event
    await manager.broadcast(
        room,
        {
            "type": "message",
            "action": "delete",
            "message_id": id,
        },
    )

    return success(None, "Message deleted")
