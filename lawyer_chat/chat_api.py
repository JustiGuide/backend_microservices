import json
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, EmailStr
from authorization import Authorizer, LiveChatMessageID, CaseChatMessageID
from database import Functions
from .chat_module import WebSocketConnection

app = APIRouter()
db_func = Functions()
chat = WebSocketConnection()

@app.get("/live/check")
@app.get("/case/check")
async def live_chat_test():
    return "Chat Routes Are Active"

class LiveChatUsername(BaseModel):
    chat_username: str


@app.get("/live/check/chat-user")
@app.get("/case/check/chat-user")
async def test_chat_user(payload: LiveChatUsername):
    return db_func.get_any_user(payload.chat_username)

@app.websocket("/ws/live/{username}")
async def live_chat(websocket: WebSocket, username: str):
    await websocket.accept()
    await chat.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            content = message["message"]
            recipient = db_func.get_any_user(message["recipient"])

            if not recipient:
                await websocket.send_text(f"User {message["recipient"]} not found")
                continue
            sender = db_func.get_immigrant(username)
            if sender:
                all_receivers = db_func.retrieve_connected_lawyers(immigrant_email=sender.email, only_emails=True)
            else:
                sender = db_func.get_lawpersonnel(username)
                all_receivers = db_func.retrieve_clients(sender.email)

            if recipient.email not in all_receivers:
                await websocket.close(code=1008, reason=f"User {message["recipient"]} not connected")
                raise WebSocketDisconnect(f"User {message["recipient"]} not connected")
            
            db_func.add_new_live_chat(sender_email=sender.email, recipient_email=recipient.email, message=content)

            await chat.send_live_message(message=content, recipient_username=recipient.username)

    except WebSocketDisconnect:
        chat.disconnect(username)


@app.websocket("/ws/case/{username}")
async def case_chat(websocket: WebSocket, username: str):
    await websocket.accept()
    await chat.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            message: dict = json.loads(data)
            content = message["message"]
            content_id = message["id"]
            recipient = db_func.get_any_user(message["recipient"])

            if not recipient:
                await websocket.send_text(f"User {message["recipient"]} not found")
                continue
            sender = db_func.get_immigrant(username)
            if sender:
                all_receivers = db_func.retrieve_connected_lawyers(
                    immigrant_email=sender.email, only_emails=True
                )
            else:
                sender = db_func.get_lawpersonnel(username)
                all_receivers = db_func.retrieve_clients(sender.email)

            if recipient.email not in all_receivers:
                await websocket.close(
                    code=1008, reason=f"User {message["recipient"]} not connected"
                )
                raise WebSocketDisconnect(f"User {message["recipient"]} not connected")

            read_status = False
            if message.get("type") == "presence":
                chat.case_chat_presence[username] = message["recipient"]
                continue

            if message.get("type") == "left":
                del chat.case_chat_presence[username]
                continue

            if recipient.username in chat.case_chat_presence:
                read_status = True
            
            db_func.add_new_case_chat(sender_email=sender.email, recipient_email=recipient.email, message=content, message_id=content_id)
            await chat.send_case_message(message=content, message_id=content_id, recipient_username=recipient.username, sender=sender)            

    except WebSocketDisconnect:
        chat.disconnect(username)

class LiveChatHistory(BaseModel):
    sender_username: str
    recipient_username: str = Depends(Authorizer.livechat_recipient_validator)


class CaseChatHistory(BaseModel):
    sender_username: str
    recipient_username: str = Depends(Authorizer.casechat_recipient_validator)


@app.get("/live/chat-history/retrieve")
async def retrieve_livechat_history(payload: LiveChatHistory):
    if not payload.sender_username or not payload.recipient_username:
        return {"error": "Check Your Data Properly, A Username is Missing."}

    recipient = db_func.get_any_user(payload.recipient_username)
    if not recipient:
        return []

    live_chat_history = db_func.retrieve_live_chat_history(sender_username=payload.sender_username, recipient_username=payload.recipient_username)
    return live_chat_history


@app.get("/case/chat-history/retrieve")
async def retrieve_casechat_history(payload: CaseChatHistory):
    if not payload.sender_username or not payload.recipient_username:
        return {"error": "Check Your Data Properly, A Username is Missing."}

    recipient = db_func.get_any_user(payload.recipient_username)
    if not recipient:
        return []

    live_chat_history = db_func.retrieve_case_chat_history(
        sender_username=payload.sender_username,
        recipient_username=payload.recipient_username,
    )
    return live_chat_history


class AddLiveChat(BaseModel):
    message: str
    sender_email: EmailStr
    recipient_email: EmailStr

@app.get("/live/chat-history/add-new-message")
async def add_new_chat_message(payload: AddLiveChat):
    if not payload.sender_email or not payload.recipient_email or not payload.message:
        return {"error": "Check Your Data Properly, Something is Missing."}

    sender = db_func.get_any_user(payload.sender_email)
    recipient = db_func.get_any_user(payload.recipient_email)
    if not sender:
        return {"status_code": 404, "message": "Sender not found"}
    if not recipient:
        return {"status_code": 404, "message": "Recipient not found"}
    
    db_func.add_new_live_chat(sender_email=payload.sender_email, recipient_email=payload.recipient_email, message=payload.message)
    return {"message": "Message Sent Successfully"}

class LiveChatID(BaseModel):
    id: LiveChatMessageID

class CaseChatID(BaseModel):
    id: CaseChatMessageID

@app.post("/live/chat-history/retrieve-single")
async def retrieve_single_livechat_message(payload: LiveChatID):
    message = db_func.retrieve_specific_live_chat_message(message_id=payload.id)

    if not message:
        return {"status_code": 404, "error": "Message Not Found."}

    sender = db_func.get_any_user(message.sender_email)
    recipient = db_func.get_any_user(message.recipient_email)

    message_response = {
        "id": message.id,
        "senderUsername": sender.username,
        "recipientUsername": recipient.username,
        "message": message.message,
        "timestamp": message.timestamp,
    }

    return message_response


@app.post("/case/chat-history/retrieve-single")
async def retrieve_single_casechat_message(payload: CaseChatID):
    message = db_func.retrieve_specific_case_chat_message(message_id=payload.id)

    if not message:
        return {"status_code": 404, "error": "Message Not Found."}

    sender = db_func.get_any_user(message.sender_email)
    recipient = db_func.get_any_user(message.recipient_email)

    message_response = {
        "id": message.id,
        "senderUsername": sender.username,
        "recipientUsername": recipient.username,
        "message": message.message,
        "starred": message.starred,
        "timestamp": message.timestamp,
    }

    return message_response

class StarCaseChat(BaseModel):
    id: CaseChatMessageID
    starred: bool = True


@app.post("/case/chat-history/star-message")
async def star_casechat_message(payload: StarCaseChat):
    if not payload.id:
        return {"error": "Check Your Data Properly, Message ID is Missing."}
    
    message = db_func.star_case_chat_message(message_id=payload.id, is_starred=payload.starred)
    return message
