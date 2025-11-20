import json
import re
from typing import Annotated
from fastapi import File, Form, HTTPException, UploadFile, status
import phonenumbers
from pydantic import (
    AfterValidator,
    BaseModel,
    EmailStr,
    Field,
    HttpUrl,
    ValidationError,
    model_validator,
)
import os
from dotenv import load_dotenv
from database import (
    Connection,
    Functions,
    LawPersonnel,
)
import datetime

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
    def notification_id_validator(id: str) -> str:
        all_ids = db_func.retrieve_all_notification_ids()
        if id not in all_ids:
            raise HTTPException(status_code=405, detail="Invalid notification ID.")
        return id


NotificationID = Annotated[
    str,
    Field(description="Notification ID."),
    AfterValidator(Authorizer.notification_id_validator),
]
