import json
from typing import Union
from fastapi import WebSocket
from helpers import Helpers
from database import Functions, Immigrants, LawPersonnel

db_func = Functions()


class WebSocketConnection:
    active_connections: dict[str, WebSocket]
    case_chat_presence: dict[str, WebSocket]

    async def connect(self, websocket: WebSocket, username: str) -> None:
        self.active_connections[username] = websocket

    def disconnect(self, username: str) -> None:
        if username in self.active_connections:
            del self.active_connections[username]

        if username in self.case_chat_presence:
            del self.case_chat_presence[username]

    async def send_live_message(self, message: str, recipient_username: str) -> None:
        receiver_socket = self.active_connections.get(recipient_username)

        if receiver_socket:
            await receiver_socket.send_text(message)

    async def send_case_message(
        self,
        message: str,
        message_id: str,
        recipient_username: str,
        sender: Union[Immigrants, LawPersonnel],
    ) -> None:
        receiver_socket = self.active_connections.get(recipient_username)
        if receiver_socket:
            read_status = True if recipient_username in self.case_chat_presence else False

            await receiver_socket.send_text(
                json.dumps(
                    {
                        "message": message,
                        "id": message_id,
                        "type": "message",
                        "read": read_status,
                    }
                )
            )

        if recipient_username not in self.case_chat_presence and self.case_chat_presence.get(recipient_username) != sender:
            sender_name = sender.full_legal_name
            recipient = db_func.get_any_user(recipient_username)
            count, message_string, notification_id = (
                db_func.retrieve_notification_count(
                    recipient_email=recipient.email,
                    type="lawyer_chat",
                    sender_email=sender.email,
                )
            )
            content = f"You have {message_string} from {sender_name}"
            if count > 0:
                content = f"You have {count+1}{message_string} from {sender_name}"

            if notification_id:
                Helpers.delete_notification(
                    recipient.email, "lawyer_chat", id=notification_id
                )
            Helpers.add_notification(
                recipient.email,
                sender.email,
                "lawyer_chat",
                content,
                {"sender": sender.email},
                one_time=True,
            )

    async def broadcast_message(self, message: str, sender: str, recipient: str) -> None:
        if sender in self.active_connections:
            await self.active_connections[sender].send_text({message})

        if recipient in self.active_connections:
            await self.active_connections[recipient].send_text({message})
