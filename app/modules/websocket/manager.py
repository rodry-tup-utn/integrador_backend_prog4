import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger("app.core.websocket")


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, set[WebSocket]] = {}
        self.socket_rooms: dict[WebSocket, set[str]] = {}

    def _join_room(self, websocket: WebSocket, room: str) -> None:
        """
        Método interno para agregar un socket a una room.

        Actualiza AMBOS mapos de datos:
          1. self.rooms[room].add(websocket)         — la room sabe que el socket está ahí
          2. self.socket_rooms[websocket].add(room)   — el socket sabe en qué rooms está

        Esta duplicación de estado es intencional: permite consultas eficientes
        en ambas direcciones (¿quién está en esta room? / ¿en qué rooms está este socket?).

        Args:
            websocket: La conexión a agregar
            room:      Nombre de la room (ej: "role:cocina", "order:5")
        """
        # Agregar socket a la room
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(websocket)

        # Agregar room al socket (mapa inverso)
        if websocket not in self.socket_rooms:
            self.socket_rooms[websocket] = set()
        self.socket_rooms[websocket].add(room)

    async def _emit_to_room(
        self, room: str, event_type: str, data: dict[str, Any]
    ) -> None:

        if room not in self.rooms:
            logger.info(f"Evento {event_type} descartado (room {room} vacía).")
            return

        payload = {"event": event_type, "data": data}
        logger.info(
            f"Emit {event_type} a room {room} ({len(self.rooms[room])} sockets)."
        )

        for connection in list(self.rooms[room]):
            try:
                await connection.send_json(payload)
            except Exception as e:
                # Conexión caída — la removemos y seguimos con las demás
                logger.warning(f"Error al enviar WebSocket. Removiendo conexión: {e}")
                self.disconnect(connection)

    async def connect(
        self, websocket: WebSocket, roles: list[str], user_id: int
    ) -> None:

        await websocket.accept()

        for role in roles:
            role_key = f"role:{role.lower()}"
            self._join_room(websocket, role_key)

            logger.info(
                f"Conexión WebSocket aceptada. user_id={user_id}, role={roles}, "
                f"room={role_key}. Total rooms activas: {len(self.rooms)}"
            )

    def disconnect(self, websocket: WebSocket) -> None:
        # Obtener y eliminar del mapa inverso
        rooms = self.socket_rooms.pop(websocket, set())

        # Remover de cada room
        for room in rooms:
            if room in self.rooms:
                self.rooms[room].discard(websocket)
                # Si la room quedó vacía, eliminarla para no acumular rooms huérfanas
                if not self.rooms[room]:
                    del self.rooms[room]

        logger.info(
            f"Conexión WebSocket finalizada. Rooms liberadas: {rooms}. "
            f"Total rooms activas: {len(self.rooms)}"
        )

    # Gestion de rooms por Pedido (clientes)

    def join_order_room(self, websocket: WebSocket, order_id: int) -> None:

        room = f"order:{order_id}"
        self._join_room(websocket, room)
        logger.info(f"Socket suscrito a room {room}")

    def leave_order_room(self, websocket: WebSocket, order_id: int) -> None:

        room = f"order:{order_id}"
        if room in self.rooms:
            self.rooms[room].discard(websocket)
            if websocket in self.socket_rooms:
                self.socket_rooms[websocket].discard(room)
            # Si la room quedó vacía, eliminarla
            if not self.rooms[room]:
                del self.rooms[room]

    async def broadcast_to_role(
        self, role: str, event_type: str, data: dict[str, Any]
    ) -> None:
        """
        Envía un evento a TODOS los sockets en la room de un rol específico.
        """
        room = f"role:{role.lower()}"
        await self._emit_to_room(room, event_type, data)

    async def broadcast_to_order(
        self, order_id: int, event_type: str, data: dict[str, Any]
    ) -> None:

        room = f"order:{order_id}"
        await self._emit_to_room(room, event_type, data)

    async def broadcast_to_roles(
        self, roles: list[str], event_type: str, data: dict[str, Any]
    ) -> None:

        sent_to: set[WebSocket] = set()
        payload = {"event": event_type, "data": data}

        for role in roles:
            room = f"role:{role.lower()}"
            if room not in self.rooms:
                continue
            for connection in list(self.rooms[room]):
                if connection not in sent_to:
                    try:
                        await connection.send_json(payload)
                        sent_to.add(connection)
                    except Exception as e:
                        # Conexión caída — la removemos y seguimos con las demás
                        logger.warning(
                            f"Error al enviar WebSocket. Removiendo conexión: {e}"
                        )
                        self.disconnect(connection)

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:

        sent_to: set[WebSocket] = set()
        payload = {"event": event_type, "data": data}

        for room_connections in self.rooms.values():
            for connection in list(room_connections):
                if connection not in sent_to:
                    try:
                        await connection.send_json(payload)
                        sent_to.add(connection)
                    except Exception as e:
                        logger.warning(
                            f"Error al enviar WebSocket. Removiendo conexión: {e}"
                        )
                        self.disconnect(connection)

    def get_active_connections_count(self) -> int:
        """
        Retorna el total de conexiones únicas activas.

        Útil para monitoreo y health checks.
        """
        return len(self.socket_rooms)

    def get_rooms_info(self) -> dict[str, int]:
        """
        Retorna información de debug: cada room y cuántos sockets tiene.

        Ejemplo de retorno:
          {
            "role:cocina": 2,
            "role:pedidos": 1,
            "order:5": 1,
          }

        Útil para endpoints de debug o monitoreo.
        """
        return {room: len(sockets) for room, sockets in self.rooms.items()}


manager = ConnectionManager()
