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
from database import Connection, LawPersonnel
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


PhoneNumber = Annotated[
    str,
    Field(description="A contact phone number, ideally in E.164 format."),
    AfterValidator(Authorizer.phonenumber_validator),
]

CaseType = Annotated[
    str, Field(description="Case type."), AfterValidator(Authorizer.casetype_validator)
]
