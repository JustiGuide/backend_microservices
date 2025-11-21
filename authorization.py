import re
from typing import Annotated
from fastapi import Form, HTTPException
import phonenumbers
from pydantic import (
    AfterValidator,
    Field,
)
import os
from dotenv import load_dotenv
from database import ChatMessage, Connection, Functions, LiveChatMessage

load_dotenv()
db_func = Functions()

class Authorizer:
    SECRET_KEY = os.getenv("OAUTH_KEY")
    AUTH_BYPASS = bool(int(os.getenv("AUTH_BYPASS")))
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 15
    Session = Connection().SessionLocal

    @staticmethod
    def phonenumber_validator(phone_str: str) -> str:
        try:
            parsed_num = phonenumbers.parse(phone_str, None)
            if not phonenumbers.is_valid_number(parsed_num):
                raise HTTPException(status_code=405, detail="Invalid phone number.")
            return phonenumbers.format_number(
                parsed_num, phonenumbers.PhoneNumberFormat.E164
            )
        except phonenumbers.NumberParseException:
            try:
                cleaned_phone = re.sub(r"[^\d+]", "", phone_str)
                if not 10 <= len(cleaned_phone) <= 15:
                    raise HTTPException(
                        status_code=405, detail=f"Invalid phone numner."
                    )
                return cleaned_phone
            except Exception as e:
                raise HTTPException(status_code=405, detail=str(e))

    @staticmethod
    def casetype_validator(casetype: str) -> str:
        valid_casetypes = [
            "nonimmigrant_worker",
            "employment_auth",
            "alien_rel",
            "asylum_removal",
            "naturalization",
        ]
        if casetype not in valid_casetypes:
            raise HTTPException(
                status_code=405,
                detail=f"Invalid case type. Must be one of {valid_casetypes}.",
            )
        return casetype

    @staticmethod
    def livechat_recipient_validator(sender_username: str = Form(...), recipient_username: str = Form(...)) -> str:
        db = Authorizer.Session()
        sender = db_func.get_immigrant(sender_username)
        recipient = db_func.get_lawpersonnel(recipient_username)
        if not sender and not recipient:
            sender = db_func.get_lawpersonnel(sender_username)
            recipient = db_func.get_immigrant(recipient_username)
            if not sender and not recipient:
                db.close()
                raise HTTPException(status_code=405, detail="Sender or Recipient not found.")
            db.close()
            lawyer_email = sender.email
            client_email = recipient.email
        else:
            lawyer_email = recipient.email
            client_email = sender.email

        if client_email not in db_func.retrieve_clients(lawyer_email=lawyer_email):
            db.close()
            raise HTTPException(
                status_code=405, detail="Client is not connected to the consultant."
            )
        all_chats = db.query(
                LiveChatMessage.sender_email, LiveChatMessage.recipient_email
            ).all()
        if recipient.email not in [
            chat[1] for chat in all_chats if chat[0] == sender.email
        ] or sender.email not in [
            chat[0] for chat in all_chats if chat[1] == recipient.email
        ]:
            db.close()
            raise HTTPException(
                status_code=405, detail="Recipient and sender are not connected"
            )
        db.close()
        return recipient_username

    @staticmethod
    def livechat_message_id_validator(message_id: str) -> str:
        db = Authorizer.Session()
        all_messages = db.query(LiveChatMessage.id).all()
        if message_id not in [message[0] for message in all_messages]:
            db.close()
            raise HTTPException(status_code=405, detail="Chat message ID is not valid.")
        db.close()
        return message_id

    @staticmethod
    def casechat_recipient_validator(
        sender_username: str = Form(...), recipient_username: str = Form(...)
    ) -> str:
        db = Authorizer.Session()
        sender = db_func.get_immigrant(sender_username)
        recipient = db_func.get_lawpersonnel(recipient_username)
        if not sender and not recipient:
            sender = db_func.get_lawpersonnel(sender_username)
            recipient = db_func.get_immigrant(recipient_username)
            if not sender and not recipient:
                db.close()
                raise HTTPException(
                    status_code=405, detail="Sender or Recipient not found."
                )
            db.close()
            lawyer_email = sender.email
            client_email = recipient.email
        else:
            lawyer_email = recipient.email
            client_email = sender.email

        if client_email not in db_func.retrieve_clients(lawyer_email=lawyer_email):
            db.close()
            raise HTTPException(
                status_code=405, detail="Client is not connected to the consultant."
            )
        all_chats = db.query(
            ChatMessage.sender_email, ChatMessage.recipient_email
        ).all()
        if recipient.email not in [
            chat[1] for chat in all_chats if chat[0] == sender.email
        ] or sender.email not in [
            chat[0] for chat in all_chats if chat[1] == recipient.email
        ]:
            db.close()
            raise HTTPException(
                status_code=405, detail="Recipient and sender are not connected"
            )
        db.close()
        return recipient_username

    @staticmethod
    def casechat_message_id_validator(message_id: str) -> str:
        db = Authorizer.Session()
        all_messages = db.query(ChatMessage.id).all()
        if message_id not in [message[0] for message in all_messages]:
            db.close()
            raise HTTPException(status_code=405, detail="Chat message ID is not valid.")
        db.close()
        return message_id


PhoneNumber = Annotated[
    str,
    Field(description="A contact phone number, ideally in E.164 format."),
    AfterValidator(Authorizer.phonenumber_validator),
]

CaseType = Annotated[
    str, Field(description="Case type."), AfterValidator(Authorizer.casetype_validator)
]

LiveChatMessageID = Annotated[
    str,
    Field(description="Chat message ID."),
    AfterValidator(Authorizer.livechat_message_id_validator),
]

CaseChatMessageID = Annotated[
    str,
    Field(description="Chat message ID."),
    AfterValidator(Authorizer.casechat_message_id_validator),
]
