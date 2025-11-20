import json
import re
from typing import Annotated, Any
from fastapi import File, Form, HTTPException, UploadFile, status
import httpx
import jwt
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
from datetime import datetime,timezone, timedelta

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

    def create_access_token(self, data: dict[str, Any]) -> str:
        to_encode = data.copy()
        issued = datetime.now(timezone.utc)
        expire = issued + timedelta(hours=self.ACCESS_TOKEN_EXPIRE_HOURS)
        if to_encode.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token: user identifier (username) missing.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        to_encode.update({"iat": issued, "exp": expire, "token_type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, data: dict[str, Any]) -> str:
        to_encode = data.copy()
        issued = datetime.now(timezone.utc)
        expire = issued + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        if to_encode.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token: user identifier (username) missing.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        to_encode.update({"iat": issued, "exp": expire, "token_type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_jwt

    @staticmethod
    async def validate_google_access_token(google_access_token: str) -> dict:
        google_token_info_url = "https://oauth2.googleapis.com/tokeninfo"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                google_token_info_url, params={"id_token": google_access_token}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=401, detail="Invalid Google access token"
                )
            return response.json()

    @staticmethod
    def google_token_validator(token: str) -> str:
        if " " in token or len(token) < 50:
            raise HTTPException(status_code=405, detail="Invalid Google Access Token")
        return token

NotificationID = Annotated[
    str,
    Field(description="Notification ID."),
    AfterValidator(Authorizer.notification_id_validator),
]
GoogleToken = Annotated[
    str,
    Field(
        description="Google OAuth2 Access Token",
        min_length=50,
        max_length=4096,
    ),
    AfterValidator(Authorizer.google_token_validator),
]
