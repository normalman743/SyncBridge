# app/routers/messages.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, utils, models
from ..permissions import get_current_user, assert_can_access_block, assert_can_post_message, assert_can_edit_message
from ..websocket_manager import manager
from typing import Optional
import asyncio

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
    current: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = crud.get_form(db, form_id)
    if not form:
        raise HTTPException(status_code=404, detail=utils.error("Form not found", "NOT_FOUND"))

    assert_can_access_block(form, current, db)

    block = crud.get_or_create_block(db, form_id, function_id, nonfunction_id)
    items, total = crud.list_messages(db, block.id, page, page_size)

    out = [
        {
            "id": m.id,
            "block_id": m.block_id,
            "user_id": m.user_id,
            "text_content": m.text_content,
            "created_at": str(m.created_at),
        }
        for m in items
    ]

    return utils.success(
        {"messages": out, "page": page, "page_size": page_size, "total": total}
    )


# ============================================================
# POST message
# (Here we add WebSocket broadcast)
# ============================================================
@router.post("/message")
def post_message(
    payload: schemas.MessageIn,
    current: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = crud.get_form(db, payload.form_id)
    if not form:
        raise HTTPException(status_code=404, detail=utils.error("Form not found", "NOT_FOUND"))

    # Check access
    assert_can_access_block(form, current, db)
    assert_can_post_message(form, current)

    # Create / get block
    block = crud.get_or_create_block(
        db, payload.form_id, payload.function_id, payload.nonfunction_id
    )

    # Create message
    msg = crud.create_message(db, block.id, current.id, payload.text_content)

    # ========== WebSocket Broadcast ==========
    room = _make_room_key(payload.form_id, payload.function_id, payload.nonfunction_id)

    asyncio.create_task(
        manager.broadcast(
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
    )
    # =========================================

    return utils.success({"message_id": msg.id}, "Message sent")


# ============================================================
# UPDATE message
# (Also broadcast update)
# ============================================================
@router.put("/message/{id}")
def update_message(
    id: int,
    changes: dict = Body(...),
    current: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = db.query(models.Message).filter(models.Message.id == id).first()
    if not msg:
        raise HTTPException(
            status_code=404, detail=utils.error("Message not found", "NOT_FOUND")
        )

    assert_can_edit_message(msg, current)

    for k, v in changes.items():
        if hasattr(msg, k):
            setattr(msg, k, v)

    db.add(msg)
    db.commit()
    db.refresh(msg)

    # WS broadcast updated content
    block = db.query(models.Block).filter(models.Block.id == msg.block_id).first()
    room = _make_room_key(block.form_id, block.target_id if block.type == "function" else None,
                          block.target_id if block.type == "nonfunction" else None)

    asyncio.create_task(
        manager.broadcast(
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
    )

    return utils.success(None, "Message updated")


# ============================================================
# DELETE message
# (Also broadcast delete)
# ============================================================
@router.delete("/message/{id}")
def delete_message(
    id: int,
    current: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = db.query(models.Message).filter(models.Message.id == id).first()
    if not msg:
        raise HTTPException(
            status_code=404, detail=utils.error("Message not found", "NOT_FOUND")
        )

    assert_can_edit_message(msg, current)

    # Get block info before deletion
    block = db.query(models.Block).filter(models.Block.id == msg.block_id).first()
    room = _make_room_key(block.form_id, block.target_id if block.type == "function" else None,
                          block.target_id if block.type == "nonfunction" else None)

    db.delete(msg)
    db.commit()

    # WS broadcast delete event
    asyncio.create_task(
        manager.broadcast(
            room,
            {
                "type": "message",
                "action": "delete",
                "message_id": id,
            },
        )
    )

    return utils.success(None, "Message deleted")
