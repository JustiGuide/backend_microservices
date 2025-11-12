from typing import Literal
from fastapi.responses import JSONResponse
from fastapi import APIRouter
from pydantic import EmailStr, Field, BaseModel
from authorization import PhoneNumber
from database import Functions
from .twilio_interpreter import TwilioInterpreter

app = APIRouter()
db_func = Functions()
interpreter = TwilioInterpreter()

class TwilioUpdate(BaseModel):
    user_num: PhoneNumber
    messages: list[str]
    comm_type: Literal["call", "text", "whatsapp"]
    user_input: str
    user_context: str
    answer: str
    ai_context: str
    method: Literal["call", "text", "whatsapp"]

class TwilioReasonUpdate(BaseModel):
    user_num: PhoneNumber
    messages: list[str]
    comm_type: str = Literal["call", "text", "whatsapp"]

@app.post("/twilio/immigrant/update-twilio")
async def update_twilioReason(payload: TwilioUpdate) -> None:
    updated_user_context = interpreter.twilio_updateContext(
        payload.user_input, payload.user_context, "USER"
    )
    updated_ai_context = interpreter.twilio_updateContext(
        f"{payload.answer}", payload.ai_context, "AI"
    )

    db_func.update_twilio_context(
        user_number=payload.user_num,
        user_context=updated_user_context,
        ai_context=updated_ai_context,
        contact_method=payload.method,
    )
    
    conversation = ""
    if payload.comm_type == "call":
        for message in payload.messages:
            conversation += f"HELPER: {message}"
    else:
        comms = ["USER", "HELPER"]
        for i, message in enumerate(payload.messages):
            conversation += f"{comms[int((i+1)%2)]}: {message}"

    reason = interpreter.twilio_conversation(conversation, payload.comm_type)
    db_func.add_twilio_interaction(
        user_number=payload.user_num,
        contact_reason=reason,
        contact_method=payload.comm_type,
    )


@app.post("/twilio/immigrant/update-twilio-reason")
async def update_twilioConveration(payload: TwilioReasonUpdate):
    conversation = ""
    if payload.comm_type == "call":
        for message in payload.messages:
            conversation += f"HELPER: {message}"
    else:
        comms = ["USER", "HELPER"]
        for i, message in enumerate(payload.messages):
            conversation += f"{comms[int((i+1)%2)]}: {message}"

    reason = interpreter.twilio_conversation(conversation, payload.comm_type)
    db_func.add_twilio_interaction(
        user_number=payload.user_num,
        contact_reason=reason,
        contact_method=payload.comm_type,
    )
