from datetime import datetime
from typing import Any, Literal
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from database import Functions
from authorization import NotificationID

db_func = Functions()
app = APIRouter()

class NewNotification(BaseModel):
    receiver: EmailStr
    sender: EmailStr
    type: Literal[
        "cases",
        "tasks",
        "connection",
        "kyc",
        "forms",
        "teams",
        "lawyer_chat",
        "intake",
        "case_payment",
    ]
    content: str
    target_id: dict[str, Any]
    one_time: bool = False
    created_at: datetime = None

@app.post("/notifications/{user_type}/add-new")
async def add_new_notification(payload: NewNotification, user_type: Literal["immigrant", "lawpersonnel"]):
    db_func.add_notification(receiver=payload.receiver,sender=payload.receiver,type=payload.type,content=payload.content,target_id=payload.target_id,one_time=payload.one_time,created_at=payload.created_at)

class DeleteNotification(BaseModel):
    email: EmailStr
    type: Literal[
        "cases",
        "tasks",
        "connection",
        "kyc",
        "forms",
        "teams",
        "lawyer_chat",
        "intake",
        "case_payment",
    ] = "connection"
    id: NotificationID = None
    data: dict[str, Any] = None
    content: str = None

@app.post("/notifications/{user_type}/remove")
async def remove_notification(payload: DeleteNotification):
    db_func.delete_notification(email=payload.email, type=payload.type, id=payload.id, data=payload.data, content=payload.content)

class NotificationCount(BaseModel):
    email: EmailStr
    type: Literal[
        "cases",
        "tasks",
        "connection",
        "kyc",
        "forms",
        "teams",
        "lawyer_chat",
        "intake",
        "case_payment",
    ]
    sender: EmailStr

@app.post("/notifications/{user_type}/retrieve-count")
async def retrieve_count(payload: NotificationCount):
    count, message_string, notification_id = db_func.retrieve_messageCount(
        email=payload.email, type=payload.type, sender=payload.sender
    )
    return {
        "count": count,
        "message": message_string,
        "id": notification_id
    }

@app.post("/notifications/{user_type}/remove-referral-notification")
async def remove_referral_notification(payload: DeleteNotification):
    db_func.remove_referred_notification(payload.email)

class NotificationIDInput(BaseModel):
    id: NotificationID

@app.post("/notifications/{user_type}/mark-individual-seen")
async def read_specific_notification(payload: NotificationIDInput):
    db_func.read_notification(payload.id)

class NotificationReciever(BaseModel):
    reciever: EmailStr

@app.post("/notifications/{user_type}/mark-all-seen")
async def read_all_notifications(payload: NotificationReciever):
    db_func.read_allNotifications(payload.reciever)

@app.post("/notifications/{user_type}/retrieve-all")
async def retrieve_all_notifications(payload: NotificationReciever):
    all_notifications = db_func.get_notifications(payload.reciever)
    return JSONResponse(all_notifications)
