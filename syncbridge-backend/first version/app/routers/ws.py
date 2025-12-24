# app/routers/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
from ..websocket_manager import manager
from .. import utils, crud, schemas
from ..database import get_db
from .. import permissions
from sqlalchemy.orm import Session

router = APIRouter()


def _room_key(form_id: int, function_id: Optional[int] = None, nonfunction_id: Optional[int] = None) -> str:
    """Return a stable room key string for given identifiers."""
    if function_id:
        return f"form:{form_id}:function:{function_id}"
    if nonfunction_id:
        return f"form:{form_id}:nonfunction:{nonfunction_id}"
    return f"form:{form_id}:general"


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket,
                             token: str = Query(None),
                             form_id: int = Query(...),
                             function_id: Optional[int] = Query(None),
                             nonfunction_id: Optional[int] = Query(None),
                             db: Session = Depends(get_db)):
    """
    WebSocket endpoint.

    Client connects with:
        /ws?token=<jwt>&form_id=123
    or
        /ws?token=<jwt>&form_id=123&function_id=45

    On connect:
    - validate token
    - ensure user has access to the form via permissions.assert_can_access_block
    - accept WS and add to room
    - handle incoming client messages (optional), but mostly server->client push is used
    """

    # Validate token
    if not token:
        await websocket.close(code=1008)  # policy violation
        return

    payload = utils.decode_access_token(token)
    if not payload:
        await websocket.close(code=1008)
        return

    uid = payload.get("sub")
    if not uid:
        await websocket.close(code=1008)
        return

    user = crud.get_user_by_id(db, int(uid))
    if not user:
        await websocket.close(code=1008)
        return

    # Validate that requested form exists and user can access its block
    form = crud.get_form(db, form_id)
    if not form:
        await websocket.close(code=1008)
        return

    # Use permissions.assert_can_access_block to make sure user can join
    try:
        permissions.assert_can_access_block(form, user, db)
    except Exception:
        # forbidden to join
        await websocket.close(code=1008)
        return

    # compute room key
    room = _room_key(form_id, function_id, nonfunction_id)

    # Accept connection
    await websocket.accept()

    # Add to manager
    await manager.connect(room, websocket)

    # Optionally notify room that a user joined
    await manager.broadcast(room, {
        "type": "presence",
        "action": "join",
        "user_id": user.id,
        "display_name": getattr(user, "display_name", None)
    })

    try:
        while True:
            # Receive messages from client (if any). We keep this loop to allow client pings.
            data = await websocket.receive_text()
            # For now, we echo back a simple ack or handle 'ping'
            if not data:
                continue
            # simple ping/pong
            if data == "ping":
                await manager.send_to(websocket, {"type": "pong"})
                continue
            # If client sends JSON messages we could handle them; we'll keep minimal:
            # ignore other client-sent messages for now
    except WebSocketDisconnect:
        # cleanup
        await manager.disconnect(room, websocket)
        await manager.broadcast(room, {
            "type": "presence",
            "action": "leave",
            "user_id": user.id,
            "display_name": getattr(user, "display_name", None)
        })
    except Exception:
        # on any other exceptions, ensure disconnect
        await manager.disconnect(room, websocket)
        await manager.broadcast(room, {
            "type": "presence",
            "action": "leave",
            "user_id": user.id,
            "display_name": getattr(user, "display_name", None)
        })
        try:
            await websocket.close()
        except Exception:
            pass
