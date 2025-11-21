import json
import re
from typing import Annotated, Any, Union
from fastapi import Form, HTTPException, status
import httpx
import jwt
import phonenumbers
from pydantic import (
    AfterValidator,
    BaseModel,
    EmailStr,
    Field,
    ValidationError,
    field_validator,
)
import os
from dotenv import load_dotenv
from database import (
    Connection,
    Functions,
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

    @staticmethod
    def validate_date(date_str: str) -> datetime.date:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date().isoformat()
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
    def validate_certificates(certificate_json: str) -> list[CertificateValidator]:
        try:
            certificate_list = json.loads(certificate_json)
            if not isinstance(certificate_list, list):
                raise HTTPException(
                    status_code=405, detail="Certificate must be a list of dictionaries."
                )
            return [CertificateValidator(**item).model_dump() for item in certificate_list]
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=405, detail="Invalid JSON format for certificate."
            )
        except ValidationError as e:
            raise HTTPException(status_code=405, detail=f"Validation error: {e}")

    @staticmethod
    def validate_lawyer_details(lawyer_json: str) -> LawyerDetailsValidator:
        try:
            lawyer_details = json.loads(lawyer_json)
            if not isinstance(lawyer_details, dict):
                raise HTTPException(
                    status_code=405, detail="Lawyer details must be a dictionary."
                )
            return LawyerDetailsValidator(**lawyer_details)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=405, detail="Invalid JSON format for lawyer details."
            )
        except ValidationError as e:
            raise HTTPException(status_code=405, detail=f"Validation error: {e}")

    @staticmethod
    def validate_paralegal_details(paralegal_json: str) -> ParalegalDetailsValidator:
        try:
            paralegal_details = json.loads(paralegal_json)
            if not isinstance(paralegal_details, dict):
                raise HTTPException(
                    status_code=405, detail="Paralegal details must be a dictionary."
                )
            return ParalegalDetailsValidator(**paralegal_details)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=405, detail="Invalid JSON format for paralegal details."
            )
        except ValidationError as e:
            raise HTTPException(status_code=405, detail=f"Validation error: {e}")

    @staticmethod
    def validate_nonlawyer_details(nonlawyer_json: str) -> NonLawyerDetailsValidator:
        try:
            nonlawyer_details = json.loads(nonlawyer_json)
            if not isinstance(nonlawyer_details, dict):
                raise HTTPException(
                    status_code=405, detail="Non-lawyer details must be a dictionary."
                )
            return NonLawyerDetailsValidator(**nonlawyer_details)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=405, detail="Invalid JSON format for non-lawyer details."
            )
        except ValidationError as e:
            raise HTTPException(status_code=405, detail=f"Validation error: {e}")

    @staticmethod
    def validate_lawstudent_details(lawstudent_json: str) -> LawStudentDetailsValidator:
        try:
            lawstudent_details = json.loads(lawstudent_json)
            if not isinstance(lawstudent_details, dict):
                raise HTTPException(
                    status_code=405, detail="Law student details must be a dictionary."
                )
            return LawStudentDetailsValidator(**lawstudent_details)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=405, detail="Invalid JSON format for law student details."
            )
        except ValidationError as e:
            raise HTTPException(status_code=405, detail=f"Validation error: {e}")

    @staticmethod
    def get_typed_details(
        personnel_type: PersonnelType = Form(...),
        details_json: str = Form(..., alias="details"),
    ) -> PersonnelDetailsUnion:
        if personnel_type == "lawyers":
            return Authorizer.validate_lawyer_details(details_json)
        elif personnel_type == "paralegals":
            return Authorizer.validate_paralegal_details(details_json)
        elif personnel_type == "nonlawyers":
            return Authorizer.validate_nonlawyer_details(details_json)
        elif personnel_type == "lawstudents":
            return Authorizer.validate_lawstudent_details(details_json)
        else:
            raise HTTPException(
                status_code=405, detail="Invalid personnel type."
            )

    @staticmethod
    def validate_experiences(experience_json: str) -> list[ExperienceValidator]:
        try:
            experience_list = json.loads(experience_json)
            if not isinstance(experience_list, list):
                raise HTTPException(
                    status_code=405, detail="Experience must be a list of dictionaries."
                )
            return [ExperienceValidator(**item).model_dump() for item in experience_list]
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=405, detail="Invalid JSON format for experience."
            )
        except ValidationError as e:
            raise HTTPException(status_code=405, detail=f"Validation error: {e}")

    @staticmethod
    def validate_personnel_type(personneltype: str) -> str:
        valid_personneltypes = ["lawyer", "paralegal", "nonlawyer", "lawstudent"]
        if personneltype[-1] == "s":
            personneltype = personneltype[:-1]
        if personneltype.lower() not in valid_personneltypes:
            raise HTTPException(
                status_code=405,
                detail=f"Invalid personnel type. Must be one of {valid_personneltypes}.",
            )
        return personneltype + "s"


PersonnelType = Annotated[
    str, Field(description="Personnel type."), AfterValidator(Authorizer.validate_personnel_type)
]
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


class CertificateValidator(BaseModel):
    is_professional: bool = True
    certificate_name: str
    issuing_organization: str
    date_issued: DateString
    expiry_date: DateString = None


class LawyerDetailsValidator(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    professional_address: str
    date_of_birth: DateString
    contact_number: PhoneNumber
    password: str
    authorize_verification: bool = True
    consent_data_collection: bool = True
    law_firm_name: str
    receive_emails: bool = True
    government_id_type: str
    experience: str
    specialty: str
    bank_accounts: list[str]
    degree: str
    institution_name: str
    field_of_study: str
    graduation_year: str
    involved_in_legal_disputes: bool
    legal_disputes_details: str
    has_professional_indemnity_insurance: bool
    insurance_coverage_details: str
    bar_association: str
    sanctioned_or_disciplined: bool
    sanction_details: str
    position: str
    nature_of_practice: str
    most_successful_case: str
    immigration_volume_per_year: str
    source_of_funds: str
    politically_exposed_person: bool

class ParalegalDetailsValidator(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    professional_address: str
    date_of_birth: DateString
    contact_number: PhoneNumber
    password: str
    authorize_verification: bool = True
    consent_data_collection: bool = True
    receive_emails: bool = True
    government_id_type: str
    specialty: str
    degree: str
    institution_name: str
    field_of_study: str
    graduation_year: str
    position_description: str
    no_legal_education: bool
    involved_in_legal_disputes: bool
    legal_disputes_details: str
    ongoing_investigations: bool
    investigations_details: str
    dismissed_or_resigned: bool
    dismissal_details: str
    disqualified_or_revoked: bool
    revocation_details: str

class NonLawyerDetailsValidator(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    professional_address: str
    date_of_birth: DateString
    contact_number: PhoneNumber
    password: str
    authorize_verification: bool = True
    consent_data_collection: bool = True
    receive_emails: bool = True
    government_id_type: str
    degree: str
    institution_name: str
    field_of_study: str
    graduation_year: str
    position: str
    position_description: str
    involved_in_legal_disputes: bool
    legal_disputes_details: str
    ongoing_investigations: bool
    investigations_details: str
    dismissed_or_resigned: bool
    dismissal_details: str


class LawStudentDetailsValidator(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    professional_address: str
    date_of_birth: DateString
    contact_number: PhoneNumber
    password: str
    authorize_verification: bool = True
    consent_data_collection: bool = True
    receive_emails: bool = True
    government_id_type: str
    degree: str
    institution_name: str
    field_of_study: str
    graduation_year: str
    involved_in_legal_disputes: bool
    legal_disputes_details: str
    ongoing_investigations: bool
    investigations_details: str
    dismissed_or_resigned: bool
    dismissal_details: str
    institution_address: str
    institution_contact: str
    attending_another_institution: bool
    other_institution_name: str
    other_degree: str
    start_year: str
    end_year: str


PersonnelDetailsUnion = Union[
    LawyerDetailsValidator,
    ParalegalDetailsValidator,
    LawStudentDetailsValidator,
    NonLawyerDetailsValidator,
]


Experiences = Annotated[
    str,
    Field(description="Experience in JSON format."),
    AfterValidator(Authorizer.validate_experiences),
]

Certificates = Annotated[
    str,
    Field(description="Certificates in JSON format."),
    AfterValidator(Authorizer.validate_certificates),
]


class ExperienceValidator(BaseModel):
    position: str
    is_current: bool = False
    organization_name: str
    duration: str
    responsibilities: str = None
    is_internship: bool = False

    @field_validator("duration")
    def duration_must_be_digits(cls, v):
        if not isinstance(v, str) or not v.isdigit():
            raise HTTPException(
                status_code=405, detail="duration must be a string of digits."
            )
        return v
