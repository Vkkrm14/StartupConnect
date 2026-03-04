import logging
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Set, Optional

from fastapi import WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from shared.auth.jwt_handler import jwt_handler
from app.core.redis import redis_manager
from app.services.message_service import message_service
from app.services.conversation_service import conversation_service
from app.services.event_producer import event_producer

logger = logging.getLogger(__name__)

INSTANCE_ID = str(uuid.uuid4())[:8]


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        self._pubsub_task: Optional[asyncio.Task] = None

    async def start_pubsub_listener(self):
        pubsub = await redis_manager.subscribe(f"ws:broadcast:{INSTANCE_ID}")
        self._pubsub_task = asyncio.create_task(self._listen_pubsub(pubsub))

        global_pubsub = await redis_manager.client.pubsub()
        await global_pubsub.subscribe("ws:broadcast:global")
        asyncio.create_task(self._listen_pubsub(global_pubsub))

    async def _listen_pubsub(self, pubsub):
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    target_user = data.get("target_user")
                    if target_user and target_user in self.active_connections:
                        await self._send_to_user_local(target_user, data.get("payload", {}))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"PubSub listener error: {e}")

    async def authenticate(self, websocket: WebSocket) -> Optional[str]:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
            return None
        try:
            payload = jwt_handler.decode_token(token)
            if payload.get("type") != "access":
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
                return None
            return payload.get("sub")
        except ValueError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return None

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        await websocket.accept()
        session_id = str(uuid.uuid4())

        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][session_id] = websocket

        await redis_manager.register_ws_session(user_id, session_id, INSTANCE_ID)
        await redis_manager.set_user_online(user_id, INSTANCE_ID)

        buffered = await redis_manager.get_buffered_messages(user_id)
        for msg in buffered:
            await self._safe_send(websocket, msg)

        logger.info(f"User {user_id} connected (session={session_id})")
        return session_id

    async def disconnect(self, user_id: str, session_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].pop(session_id, None)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        await redis_manager.remove_ws_session(user_id, session_id)
        logger.info(f"User {user_id} disconnected (session={session_id})")

    async def send_to_user(self, user_id: str, payload: dict):
        if user_id in self.active_connections:
            await self._send_to_user_local(user_id, payload)
        else:
            sessions = await redis_manager.get_user_sessions(user_id)
            if sessions:
                for session_id, instance in sessions.items():
                    if instance == INSTANCE_ID:
                        continue
                    await redis_manager.publish(
                        f"ws:broadcast:{instance}",
                        {"target_user": user_id, "payload": payload},
                    )
            else:
                await redis_manager.buffer_message(user_id, payload)

    async def _send_to_user_local(self, user_id: str, payload: dict):
        if user_id not in self.active_connections:
            return
        dead_sessions = []
        for session_id, ws in self.active_connections[user_id].items():
            success = await self._safe_send(ws, payload)
            if not success:
                dead_sessions.append(session_id)
        for sid in dead_sessions:
            await self.disconnect(user_id, sid)

    async def _safe_send(self, websocket: WebSocket, data: dict) -> bool:
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(data)
                return True
        except Exception:
            return False
        return False

    async def handle_message(self, user_id: str, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        action = data.get("action")

        if action == "send_message":
            await self._handle_send_message(user_id, data)
        elif action == "typing":
            await self._handle_typing(user_id, data)
        elif action == "stop_typing":
            await self._handle_stop_typing(user_id, data)
        elif action == "read_receipt":
            await self._handle_read_receipt(user_id, data)
        elif action == "heartbeat":
            await redis_manager.heartbeat(user_id)
            await self.send_to_user(user_id, {"event": "heartbeat_ack", "ts": datetime.utcnow().isoformat()})

    async def _handle_send_message(self, user_id: str, data: dict):
        conversation_id = data.get("conversation_id")
        encrypted_payload = data.get("encrypted_payload")
        message_type = data.get("message_type", "text")
        encrypted_key = data.get("encrypted_key")
        metadata = data.get("metadata")

        if not conversation_id or not encrypted_payload:
            await self.send_to_user(user_id, {"event": "error", "message": "Missing required fields"})
            return

        is_participant = await conversation_service.is_participant(conversation_id, user_id)
        if not is_participant:
            await self.send_to_user(user_id, {"event": "error", "message": "Not a conversation participant"})
            return

        recipient = await conversation_service.get_other_participant(conversation_id, user_id)
        if recipient and await conversation_service.is_blocked(user_id, recipient):
            await self.send_to_user(user_id, {"event": "error", "message": "Cannot send message"})
            return

        allowed = await redis_manager.check_rate_limit(user_id, 60)
        if not allowed:
            await self.send_to_user(user_id, {"event": "error", "message": "Rate limit exceeded"})
            return

        message = await message_service.store_message(
            conversation_id=conversation_id,
            sender_id=user_id,
            encrypted_payload=encrypted_payload,
            message_type=message_type,
            encrypted_key=encrypted_key,
            metadata=metadata,
        )

        await conversation_service.update_last_message(
            conversation_id=conversation_id,
            message_type=message_type,
            timestamp=datetime.utcnow(),
            preview=f"[{message_type}]",
        )

        outbound = {"event": "new_message", **message}

        await self.send_to_user(user_id, outbound)
        if recipient:
            await self.send_to_user(recipient, outbound)

        await redis_manager.clear_typing(user_id, conversation_id)
        await event_producer.emit_message_sent(message)

    async def _handle_typing(self, user_id: str, data: dict):
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            return
        await redis_manager.set_typing(user_id, conversation_id)
        recipient = await conversation_service.get_other_participant(conversation_id, user_id)
        if recipient:
            await self.send_to_user(
                recipient,
                {"event": "typing", "conversation_id": conversation_id, "user_id": user_id},
            )

    async def _handle_stop_typing(self, user_id: str, data: dict):
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            return
        await redis_manager.clear_typing(user_id, conversation_id)
        recipient = await conversation_service.get_other_participant(conversation_id, user_id)
        if recipient:
            await self.send_to_user(
                recipient,
                {"event": "stop_typing", "conversation_id": conversation_id, "user_id": user_id},
            )

    async def _handle_read_receipt(self, user_id: str, data: dict):
        conversation_id = data.get("conversation_id")
        message_id = data.get("message_id")
        if not conversation_id or not message_id:
            return

        recipient = await conversation_service.get_other_participant(conversation_id, user_id)
        if recipient:
            await self.send_to_user(
                recipient,
                {
                    "event": "read_receipt",
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "reader_id": user_id,
                    "read_at": datetime.utcnow().isoformat(),
                },
            )
        await event_producer.emit_message_read(conversation_id, user_id, message_id)


connection_manager = ConnectionManager()
