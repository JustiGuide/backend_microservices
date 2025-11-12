import re
from typing import Annotated
from fastapi import File, Form, HTTPException, UploadFile, status
import phonenumbers
from pydantic import AfterValidator, EmailStr, Field
import os
from dotenv import load_dotenv
from database import Connection, Functions, ImmigrantAIChat, Immigrants, LawPersonnel, LawPersonnelAIChat
import datetime

load_dotenv()

class Authorizer:
    SECRET_KEY = os.getenv("OAUTH_KEY")
    AUTH_BYPASS = bool(int(os.getenv("AUTH_BYPASS")))
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 15
    Session = Connection().SessionLocal

    @staticmethod
    def immigrant_chatlimit(username: str) -> str:
        db = Authorizer.Session()
        immigrant = db.query(Immigrants).filter(Immigrants.username == username).first()
        if immigrant.chat_limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chat limit exceeded. Please upgrade your plan to continue using the AI chat features.",
            )

    @staticmethod
    def immigrant_agent_selection(agent_selection: str) -> str:
        valid_agents = ["relo", "dolores", "form", "help", "n400"]
        if agent_selection.lower() not in valid_agents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent selection. Choose from {', '.join(valid_agents)}.",
            )
        return agent_selection.lower()

    @staticmethod
    def lawpersonnel_agent_selection(agent_selection: str) -> str:
        valid_agents = ["form", "help", "lawyer"]
        if agent_selection.lower() not in valid_agents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent selection. Choose from {', '.join(valid_agents)}.",
            )
        return agent_selection.lower()

    @staticmethod    
    def validate_timestamp(timestamp_str: str) -> str:
        if timestamp_str.isdigit():
            if len(timestamp_str) == 10:
                try:
                    datetime.datetime.fromtimestamp(int(timestamp_str)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    return timestamp_str
                except ValueError:
                    raise HTTPException(status_code=405, detail="Invalid timestamp.")
            elif len(timestamp_str) == 13:
                try:
                    datetime.datetime.fromtimestamp(int(timestamp_str) / 1000).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    return timestamp_str
                except ValueError:
                    raise HTTPException(status_code=405, detail="Invalid timestamp.")
            else:
                raise HTTPException(status_code=405, detail="Invalid timestamp format.")
        else:
            raise HTTPException(status_code=405, detail="Timestamp must be a number.")

    @staticmethod
    def formnames(form_name: str) -> str:
        valid_form_names = ["i129", "i130", "i589", "i765", "n400"]
        if form_name.lower() not in valid_form_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid form selection. Choose from {', '.join(valid_form_names)}"
            )
        return form_name.lower()

    @staticmethod
    def immigrant_ai_validator(immigrant_email: EmailStr) -> EmailStr:
        db = Authorizer.Session()
        messages = db.query(ImmigrantAIChat.immigrant_email).all()
        if immigrant_email not in [message[0] for message in messages]:
            db.close()
            raise HTTPException(status_code=405, detail="Immigrant has no messages.")
        db.close()
        return immigrant_email

    @staticmethod
    def lawpersonnel_ai_validator(lawpersonnel_email: EmailStr) -> EmailStr:
        db = Authorizer.Session()
        messages = db.query(LawPersonnelAIChat.lawpersonnel_email).all()
        if lawpersonnel_email not in [message[0] for message in messages]:
            db.close()
            raise HTTPException(status_code=405, detail="Lawpersonnel has no messages.")
        db.close()
        return lawpersonnel_email

    @staticmethod
    def lawpersonnel_message_validator(lawpersonnel_username: str = Form(...), message_id: str = Form(...)) -> str:
        db = Authorizer.Session()
        lawpersonnel = Functions().get_lawpersonnel(lawpersonnel_username)
        if not lawpersonnel:
            raise HTTPException(status_code=405, detail="Lawpersonnel not found.")
        all_message_ids = db.query(LawPersonnelAIChat.uuid, LawPersonnelAIChat.lawpersonnel_email).all()
        if message_id not in [id[0] for id in all_message_ids if id[1] == lawpersonnel.email]:
            db.close()
            raise HTTPException(
                status_code=405, detail="Invalid AI message ID for the lawpersonnel."
            )
        db.close()
        return message_id

    @staticmethod
    def audio_file_validator(audio: UploadFile) -> UploadFile:
        if audio.content_type not in [
            "audio/wave",
            "audio/wav",
            "audio/x-wav",
            "audio/flac",
            "audio/mp3",
            "audio/mp4",
            "audio/mpeg",
            "audio/mpga",
            "audio/oga",
            "audio/ogg",
            "audio/webm",
        ]:
            raise HTTPException(status_code=400, detail="Invalid audio file type")
        return audio

    @staticmethod
    def client_email_validator(immigrant_email: EmailStr = Form(...), lawpersonnel_username: str = Form(...)) -> EmailStr:
        # TODO: Connect with relationship management service
        return immigrant_email

    @staticmethod
    def validate_date(date_str: str) -> datetime.date:
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d").date().isoformat()
        except ValueError:
            raise HTTPException(
                status_code=405, detail="Invalid date format. Use YYYY-MM-DD."
            )
        
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
                    raise HTTPException(status_code=405, detail=f"Invalid phone numner.")
                return cleaned_phone
            except Exception as e:
                raise HTTPException(status_code=405, detail=str(e))


ImmigrantChatLimitValidator = Annotated[
    str,
    Field(description="Immigrant Chat Limit Validator"),
    AfterValidator(Authorizer.immigrant_chatlimit)
]

ImmigrantAgentValidator = Annotated[
    str,
    Field(description="Immigrant Agent Selection Validator"),
    AfterValidator(Authorizer.immigrant_agent_selection)
]

LawPersonnelAgentValidator = Annotated[
    str,
    Field(description="Lawpersonnel Agent Selection Validator"),
    AfterValidator(Authorizer.lawpersonnel_agent_selection)
]

FormNameValidator = Annotated[
    str,
    Field(description="Form Selection Validator"),
    AfterValidator(Authorizer.formnames)
]

TimestampValidator = Annotated[
    str,
    Field(description="Timestamp Validator"),
    AfterValidator(Authorizer.validate_timestamp)
]

ImmigrantAIValidator = Annotated[
    str,
    Field(description="Immigrant AI Validator"),
    AfterValidator(Authorizer.immigrant_ai_validator),
]

LawpersonnelAIValidator = Annotated[
    str,
    Field(description="Lawpersonnel AI Validator"),
    AfterValidator(Authorizer.lawpersonnel_ai_validator),
]

AudioFile = Annotated[
    UploadFile,
    File(description="An audio file"),
    AfterValidator(Authorizer.audio_file_validator),
]

DateString = Annotated[
    str,
    Field(
        description="A date string in YYYY-MM-DD format.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    AfterValidator(Authorizer.validate_date),
]
PhoneNumber = Annotated[
    str,
    Field(description="A contact phone number, ideally in E.164 format."),
    AfterValidator(Authorizer.phonenumber_validator),
]
