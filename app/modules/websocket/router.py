import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.modules.websocket.manager import manager
from app.modules.auth.dependencies import get_token_payload
from app.core.exceptions import AuthenticationError

logger = logging.getLogger("app.modules.websocket.router")
router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    try:
        token = websocket.cookies.get("access_token")
        if not token:
            await websocket.close(code=1008)
            return

        payload = get_token_payload(token)

        user_id = payload.id
        roles = payload.roles

        if not user_id or not roles:
            await websocket.close(code=1008)
            return

        await manager.connect(websocket, roles, user_id)

        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "subscribe-order":
                order_id = data.get("order_id")
                if order_id:
                    manager.join_order_room(websocket, order_id)
                    await websocket.send_json(
                        {
                            "status": "subscribed",
                            "order_id": order_id,
                        }
                    )
            elif action == "unsubscribe-order":
                order_id = data.get("order_id")
                if order_id:
                    manager.leave_order_room(websocket, order_id)
                    await websocket.send_json(
                        {
                            "status": "unsubscribed",
                            "order_id": order_id,
                        }
                    )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except AuthenticationError:
        await websocket.close(code=1008)
        manager.disconnect(websocket)

    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        manager.disconnect(websocket)
