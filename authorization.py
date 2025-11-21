import re
from typing import Annotated
from fastapi import HTTPException, status
import phonenumbers
from pydantic import (
    AfterValidator,
    EmailStr,
    Field,
    HttpUrl,
)
import os
from dotenv import load_dotenv
from database import (
    Connection,
    Functions,
)

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
    def connected_lawyer_validator(lawpersonnel_email: EmailStr, immigrant_email: EmailStr) -> EmailStr:
        all_emails = db_func.retrieve_conn_lawyer_emails(immigrant_email=immigrant_email)
        if lawpersonnel_email not in all_emails:
            raise HTTPException(status_code=405, detail="Lawyer is not connected.")
        return lawpersonnel_email

    @staticmethod
    def unsaved_lawyer_validator(lawpersonnel_email: EmailStr, immigrant_email: EmailStr) -> EmailStr:
        all_saved = db_func.get_saved_lawyers(immigrant_email=immigrant_email)
        if lawpersonnel_email in all_saved:
            raise HTTPException(status_code=405, detail="This lawyer is already saved.")
        return lawpersonnel_email

    @staticmethod
    def saved_lawyer_validator(
        lawpersonnel_email: EmailStr, immigrant_email: EmailStr
    ) -> EmailStr:
        all_saved = db_func.get_saved_lawyers(immigrant_email=immigrant_email)
        if lawpersonnel_email not in all_saved:
            raise HTTPException(status_code=405, detail="This lawyer is not saved.")
        return lawpersonnel_email

    @staticmethod
    def formnames(form_name: str) -> str:
        valid_form_names = db_func.get_all_formnames()
        if form_name.lower() not in valid_form_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid form selection. Choose from {', '.join(valid_form_names)}",
            )
        return form_name.lower()

    @staticmethod
    def case_intake_validator(case_id: str, intake_id: str) -> str:
        lawyer_email = db_func.retrieve_case_lawyer(case_id)
        all_forms = db_func.retrieve_intake_form_ids(lawyer_email)
        if intake_id not in all_forms:
            raise HTTPException(status_code=405, detail="Form ID is not connected to the lawyer.")
        return intake_id

    @staticmethod
    def lawyer_intake_validator(intake_id: str, lawyer_email: str) -> str:
        all_forms = db_func.retrieve_intake_form_ids(lawyer_email)
        if intake_id not in all_forms:
            raise HTTPException(
                status_code=405, detail="Form ID is not connected to the lawyer."
            )
        return intake_id

    @staticmethod
    def intake_id_validator(intake_id: str) -> str:
        all_forms = db_func.retrieve_all_form_ids()
        if intake_id not in all_forms:
            raise HTTPException(
                status_code=405, detail="Form ID is not connected to the lawyer."
            )
        return intake_id

    @staticmethod
    def intake_url_validator(intake_id: str, intake_url: HttpUrl) -> str:
        all_forms = db_func.retrieve_lawyer_form_url(intake_id)
        if str(intake_url) not in all_forms:
            raise HTTPException(status_code=405, detail="Form URL is not connected to the form ID.")
        return str(intake_url)

    @staticmethod
    def pending_lawyer_validator(immigrant_email: EmailStr, lawyer_email: EmailStr) -> EmailStr:
        all_pending = db_func.retrieve_pending_lawyers(immigrant_email)
        if lawyer_email not in all_pending:
            raise HTTPException(status_code=405, detail="This lawyer is not pending.")
        return lawyer_email

    @staticmethod
    def pending_client_validator(
        immigrant_email: EmailStr, lawyer_email: EmailStr
    ) -> EmailStr:
        all_pending = db_func.retrieve_pending_client(lawyer_email)
        if immigrant_email not in all_pending:
            raise HTTPException(status_code=405, detail="This client is not pending.")
        return immigrant_email

    @staticmethod
    def lawyer_client_validator(immigrant_email: EmailStr, lawpersonnel_email: EmailStr) -> EmailStr:
        all_clients = db_func.retrieve_all_clients(lawpersonnel_email)
        if immigrant_email not in all_clients:
            raise HTTPException(
                status_code=405, detail="Client is not connected to the lawyer."
            )
        return lawpersonnel_email

PhoneNumber = Annotated[
    str,
    Field(description="A contact phone number, ideally in E.164 format."),
    AfterValidator(Authorizer.phonenumber_validator),
]

FormNameValidator = Annotated[
    str,
    Field(description="Form Selection Validator"),
    AfterValidator(Authorizer.formnames),
]

FormIDInput = Annotated[
    str,
    Field(description="Intake form ID."),
    AfterValidator(Authorizer.intake_id_validator),
]
