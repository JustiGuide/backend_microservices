import re
from typing import Annotated
from fastapi import File, Form, HTTPException, UploadFile, status
import phonenumbers
from pydantic import AfterValidator, EmailStr, Field
import os
from dotenv import load_dotenv
from database import (
    Connection,
    LawyerCaseSubs,
    SubscriptionDetails
)
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
    def client_email_validator(
        client_email: EmailStr, lawpersonnel_email: EmailStr
    ) -> EmailStr:
        # TODO: Connect with relationship management service
        return client_email

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
                    raise HTTPException(
                        status_code=405, detail=f"Invalid phone numner."
                    )
                return cleaned_phone
            except Exception as e:
                raise HTTPException(status_code=405, detail=str(e))

    @staticmethod
    def subscriber_email_validator(subscriber_email: EmailStr) -> EmailStr:
        db = Authorizer.Session()
        all_emails = db.query(SubscriptionDetails.user_email).all()
        if subscriber_email not in [email[0] for email in all_emails]:
            db.close()
            raise HTTPException(status_code=405, detail="Invalid user email.")
        db.close()
        return subscriber_email

    @staticmethod
    def subscription_tier_validator(tier: str) -> str:
        valid_tiers = ["free", "plus", "enterprise", "pay", "nonlawyer", "lawyer", "clinic"]
        if tier not in valid_tiers:
            raise HTTPException(status_code=405, detail=f"Invalid tier. Must be one of {valid_tiers}.")
        return tier

    @staticmethod
    def subscription_duration_validator(duration: str) -> str:
        valid_durations = ["monthly", "yearly"]
        if duration not in valid_durations:
            raise HTTPException(status_code=405, detail=f"Invalid tier. Must be one of {valid_durations}.")
        return duration

    @staticmethod
    def casetype_validator(casetype: str) -> str:
        valid_casetypes = [
            "nonimmigrant_worker",
            "employment_auth",
            "alien_rel",
            "asylum_removal",
            "naturalization"
        ]
        if casetype not in valid_casetypes:
            raise HTTPException(status_code=405, detail=f"Invalid case type. Must be one of {valid_casetypes}.")
        return casetype

    @staticmethod
    def lawyer_case_validator(
        case_id: str, lawyer_email: EmailStr
    ) -> str:
        # TODO: Connect with case management service
        return case_id

    @staticmethod
    def subcase_id_validator(case_id: str) -> str:
        db = Authorizer.Session()
        all_cases = db.query(LawyerCaseSubs.case_id).all()
        if case_id not in [case[0] for case in all_cases]:
            db.close()
            raise HTTPException(status_code=405, detail="Invalid case ID.")
        db.close()
        return case_id

TimestampValidator = Annotated[
    str,
    Field(description="Timestamp Validator"),
    AfterValidator(Authorizer.validate_timestamp),
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

SubscriberEmail = Annotated[
    str,
    Field(description="Subscriber email."),
    AfterValidator(Authorizer.subscriber_email_validator)
]
SubscriptionTier = Annotated[
    str,
    Field(description="Subscription tier for immigrant dashboard."),
    AfterValidator(Authorizer.subscription_tier_validator),
]
SubscriptionDuration = Annotated[
    str,
    Field(description="Subscription duration."),
    AfterValidator(Authorizer.subscription_duration_validator),
]
CaseType = Annotated[
    str, Field(description="Case type."), AfterValidator(Authorizer.casetype_validator)
]

SubCaseID = Annotated[
    str,
    Field(description="Sub-case ID."),
    AfterValidator(Authorizer.subcase_id_validator),
]

LawyerCaseID = Annotated[
    str,
    Field(description="Lawyer's case ID"),
    AfterValidator(Authorizer.lawyer_case_validator)
]
