import os
from typing import Annotated
from dotenv import load_dotenv
from fastapi import Form, HTTPException, status
from pydantic import AfterValidator, EmailStr, Field
from database import Connection, Functions
from bucket_management.bucket_console import BucketConsole

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
    def file_url_validator(file_url: str = Form(...)) -> str:
        if not file_url.startswith(BucketConsole.base_url):
            raise HTTPException(status_code=405, detail="Invalid S3 File URL.")
        return file_url

    @staticmethod
    def dir_url_validator(directory: str = Form(...)) -> str:
        if directory.startswith("https") and not directory.startswith(
            BucketConsole.base_url
        ):
            raise HTTPException(status_code=405, detail="Invalid S3 Directory URL.")
        return directory

    @staticmethod
    def file_key_validator(file_key: str = Form(...)) -> str:
        if file_key.startswith("https"):
            raise HTTPException(status_code=405, detail="Invalid S3 File Key.")
        return file_key

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
    def client_email_validator(
        immigrant_email: EmailStr = Form(...), lawpersonnel_username: str = Form(...)
    ) -> EmailStr:
        # TODO: Connect with relationship management service
        return immigrant_email

    @staticmethod
    def client_signid_validator(sign_id: str = Form(...), client_email: EmailStr = Form(...)) -> str:
        all_signs = db_func.retrieve_all_signs(client_email)
        if sign_id not in [sign.uuid for sign in all_signs if sign.user_email == client_email]:
            print("Lawyer email not found in clients.")
            raise HTTPException(status_code=405, detail="Sign is not connected to the email.")
        return sign_id

    @staticmethod
    def user_signid_validator(
        sign_id: str = Form(...), user_email: EmailStr = Form(...)
    ) -> str:
        all_signs = db_func.retrieve_all_signs(user_email)
        if sign_id not in [
            sign.uuid for sign in all_signs if sign.user_email == user_email
        ]:
            raise HTTPException(
                status_code=405, detail="Sign is not connected to the email."
            )
        return sign_id

    @staticmethod
    def sign_id_validator(sign_id: str = Form(...)) -> str:
        all_signs = db_func.retrieve_every_sign()
        if sign_id not in [
            sign.uuid for sign in all_signs
        ]:
            raise HTTPException(
                status_code=405, detail="Sign is not connected to the email."
            )
        return sign_id


S3FileUrl = Annotated[
    str,
    Field(description="S3 Bucket File URL"),
    AfterValidator(Authorizer.file_url_validator)
]

S3DirUrl = Annotated[
    str,
    Field(description="S3 Bucket Directory URL"),
    AfterValidator(Authorizer.dir_url_validator),
]

S3FileKey = Annotated[
    str,
    Field(description="S3 Bucket File Key"),
    AfterValidator(Authorizer.file_key_validator),
]

FormNameValidator = Annotated[
    str,
    Field(description="Form Selection Validator"),
    AfterValidator(Authorizer.formnames),
]

UserSignID = Annotated[
    str,
    Field(description="User Sign ID Validator"),
    AfterValidator(Authorizer.user_signid_validator),
]

SignID = Annotated[
    str,
    Field(description="Sign ID Validator"),
    AfterValidator(Authorizer.sign_id_validator),
]
