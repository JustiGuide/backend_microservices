import math
import os
from random import randint
import re
from typing import Any, Union, Literal
from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from sqlalchemy import (
    TIMESTAMP,
    Column,
    Date,
    Float,
    Integer,
    String,
    Text,
    Boolean,
    create_engine,
    func,
)
from encryptor import EncryptedText, Encrypt
from datetime import date, datetime, timedelta

load_dotenv()
Base = declarative_base()
encr = Encrypt()

class NotificationAlerts(Base):
    __tablename__ = "notification_alerts"

    id = Column(String, primary_key=True, default=Encrypt.generate_uuid)
    receiver = Column(EncryptedText, nullable=False, index=True)
    sender = Column(EncryptedText, nullable=False)
    type = Column(EncryptedText, nullable=False)
    content = Column(EncryptedText, nullable=False)
    target_id = Column(EncryptedText, nullable=False)
    one_time = Column(Boolean, nullable=False, default=False)
    seen = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "receiver": self.receiver,
            "sender": self.sender,
            "type": self.type,
            "content": self.content,
            "target_id": self.target_id,
            "one_time": self.one_time,
            "seen": self.seen,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def __repr__(self):
        return f"<NotificationAlerts(id={self.id}, receiver={self.receiver}, sender={self.sender}, type={self.type}, content={self.content}, target_id={self.target_id}, one_time={self.one_time}, seen={self.seen})>"

    def update_created_at(self):
        self.created_at = func.now()

class Immigrants(Base):
    __tablename__ = "immigrants"
    username: str = Column(EncryptedText, index=True, nullable=False, unique=True)
    email: EmailStr = Column(
        EncryptedText, primary_key=True, nullable=False, unique=True
    )
    first_name: str = Column(EncryptedText, nullable=False)
    last_name: str = Column(EncryptedText, nullable=True)
    full_legal_name: str = Column(EncryptedText, nullable=False)
    location: str = Column(EncryptedText, nullable=True)
    hashed_password: str = Column(String(128), nullable=True)
    subscription_type: str = Column(String(20), default="free", nullable=False)
    profile_pic: str = Column(Text, nullable=False)
    chat_limit: float = Column(Float, default=10.0, nullable=False)
    data_collection: bool = Column(Boolean, default=True, nullable=False)
    receive_emails: bool = Column(Boolean, default=True, nullable=False)
    contact_number: str = Column(EncryptedText, nullable=True)
    date_of_birth: str = Column(EncryptedText, nullable=True)
    receipt_number: str = Column(EncryptedText, nullable=True)

    def extract_data(self) -> dict[str, Union[str, EmailStr]]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "location": self.location,
        }

    @property
    def password(self):
        raise AttributeError("Password is not readable.")

    @password.setter
    def password(self, plain_password):
        self.hashed_password = encr.hash_password(plain_password)

    def verify_password(self, plain_password):
        return encr.verify_password(plain_password, self.hashed_password)

class LawPersonnel(Base):
    __tablename__ = "law_personnel"

    # General Personnel Fields
    email: EmailStr = Column(EncryptedText, nullable=False, primary_key=True)
    username: str = Column(EncryptedText, nullable=False)
    hashed_password: str = Column(String, nullable=False)
    firstName: str = Column(EncryptedText, nullable=False)
    lastName: str = Column(EncryptedText, nullable=True)
    full_legal_name: str = Column(EncryptedText, nullable=False)
    profile_picture: str = Column(
        EncryptedText,
        nullable=False,
        default="https://doloreschatbucket.s3.us-east-2.amazonaws.com/lawyer-connections/template-pp.png",
    )
    contact_number = Column(EncryptedText, nullable=False)
    date_of_birth: str = Column(EncryptedText, nullable=True)
    professional_address: str = Column(EncryptedText, nullable=False)
    personnel_type: str = Column(String, nullable=False)
    verified: bool = Column(Boolean, nullable=True, default=False)
    subscription_tier: str = Column(String, nullable=False, default="free")
    receive_emails: bool = Column(Boolean, nullable=False, default=False)
    authorize_verification: bool = Column(Boolean, nullable=False, default=False)
    consent_data_collection: bool = Column(Boolean, nullable=False, default=False)

    # Lawyer-Specific Fields
    law_firm_name: str = Column(EncryptedText, nullable=True)
    experience: str = Column(EncryptedText, nullable=True)
    specialty: str = Column(EncryptedText, nullable=True)

    # General Details Object containing additional information.
    details: dict = Column(EncryptedText, nullable=False)

    # Validate Password
    @property
    def password(self):
        raise AttributeError("Password is not readable.")

    # Set Hashed Password
    @password.setter
    def password(self, plain_password):
        self.hashed_password = encr.hash_password(plain_password)

    # Password Verification Method
    def verify_password(self, plain_password):
        return encr.verify_password(plain_password, self.hashed_password)

    def extract_data(self) -> dict[str, Union[str, EmailStr]]:
        return {
            "email": self.email,
            "username": self.username,
            "firstName": self.firstName,
            "lastName": self.lastName,
            "profile_picture": self.profile_picture,
            "contact_number": self.contact_number,
            "date_of_birth": self.date_of_birth,
            "professional_address": self.professional_address,
            "personnel_type": self.personnel_type,
            "verified": self.verified,
            "subscription_tier": self.subscription_tier,
            "receive_emails": self.receive_emails,
            "authorize_verification": self.authorize_verification,
            "consent_data_collection": self.consent_data_collection,
            "law_firm_name": self.law_firm_name,
            "experience": self.experience,
            "specialty": self.specialty,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return f"<LawPersonnel(email={self.email}, username={self.username}, firstName={self.firstName}, lastName={self.lastName}, personnel_type={self.personnel_type})>"

class ExternalLawyer(Base):
    __tablename__ = "external_lawyers"
    firstName: str = Column(EncryptedText, nullable=False)
    lastName: str = Column(EncryptedText, nullable=False)
    fullName: str = Column(EncryptedText, nullable=False)
    username: str = Column(EncryptedText, primary_key=True, nullable=False)
    email: EmailStr = Column(EncryptedText, nullable=False)
    lawFirmName: str = Column(EncryptedText, nullable=True)
    expertise: str = Column(String, nullable=True)
    experience: str = Column(String, nullable=True)
    professionalAddress: str = Column(EncryptedText, nullable=True)
    contactNumber: str = Column(EncryptedText, nullable=True)
    profilePicture: str = Column(
        EncryptedText,
        nullable=False,
        default="https://doloreschatbucket.s3.us-east-2.amazonaws.com/lawyer-connections/template-pp.png",
    )

    def to_dict(self) -> dict[str, Union[str, EmailStr]]:
        return {
            "firstName": self.firstName,
            "lastName": self.lastName,
            "fullName": self.fullName,
            "username": self.username,
            "email": self.email,
            "lawFirmName": self.lawFirmName,
            "expertise": self.expertise,
            "experience": self.experience,
            "professionalAddress": self.professionalAddress,
            "contactNumber": self.contactNumber,
            "profilePicture": self.profilePicture,
        }

    def __repr__(self) -> str:
        return f"<ExternalLawyer(username={self.username}, fullName={self.fullName}, email={self.email})>"

class LawyerStats(Base):
    __tablename__ = "lawyer_stats"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawyer_email = Column(EncryptedText, nullable=False)
    stat_date = Column(Date, nullable=False)
    stat_type = Column(String(50), nullable=False)
    stat_val = Column(Integer, nullable=False, default=1)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "lawyer_email": self.lawyer_email,
            "stat_date": self.stat_date,
            "stat_type": self.stat_type,
            "stat_val": self.stat_val,
        }

    def __repr__(self):
        return f"<LawyerStats(uuid={self.uuid}, lawyer_email={self.lawyer_email}, stat_date={self.stat_date}, stat_type={self.stat_type}, stat_val={self.stat_val})>"

class ImmigrantKYC(Base):
    __tablename__ = "immigrant_kyc"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    immigrant_email = Column(EncryptedText, nullable=False, index=True)
    kyc_details = Column(EncryptedText, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "immigrant_email": self.immigrant_email,
            "kyc_details": self.kyc_details,
        }

    def __repr__(self):
        return f"<ImmigrantKYC(uuid={self.uuid}, immigrant_email={self.immigrant_email}, kyc_details={self.kyc_details})>"

class UsersVerification(Base):
    __tablename__ = "users_verification"
    email = Column(EncryptedText, primary_key=True, nullable=False)
    verification_code = Column(String(4), nullable=False)

    def extract_data(self):
        return {
            "email": self.email,
            "verification_code": self.verification_code,
        }

class LawPersonnelCertificates(Base):
    __tablename__ = "lawpersonnel_certificates"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawpersonnel_email = Column(EncryptedText, nullable=False, index=True)
    lawpersonnel_type = Column(EncryptedText, nullable=False)
    certificate_name = Column(EncryptedText, nullable=False)
    issuing_organization = Column(EncryptedText, nullable=False)
    date_issued = Column(EncryptedText, nullable=False)
    expiry_date = Column(EncryptedText, nullable=True)
    is_professional = Column(EncryptedText, nullable=True)
    certificate_url = Column(EncryptedText, nullable=True)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "lawpersonnel_email": self.lawpersonnel_email,
            "lawpersonnel_type": self.lawpersonnel_type,
            "certificate_name": self.certificate_name,
            "issuing_organization": self.issuing_organization,
            "date_issued": self.date_issued,
            "expiry_date": self.expiry_date,
            "is_professional": self.is_professional,
            "certificate_url": self.certificate_url,
        }

    def __repr__(self):
        return f"<LawPersonnelCertificates(uuid={self.uuid}, lawpersonnel_email={self.lawpersonnel_email}, lawpersonnel_type={self.lawpersonnel_type}, certificate_name={self.certificate_name}, issuing_organization={self.issuing_organization}, date_issued={self.date_issued}, expiry_date={self.expiry_date}, is_professional={self.is_professional}, certificate_url={self.certificate_url})>"

class LawPersonnelExperiences(Base):
    __tablename__ = "lawpersonnel_experiences"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawpersonnel_email = Column(EncryptedText, nullable=False, index=True)
    organization_name = Column(EncryptedText, nullable=False)
    lawpersonnel_type = Column(EncryptedText, nullable=False)
    is_current = Column(Boolean, nullable=False, default=False)
    position = Column(EncryptedText, nullable=False)
    duration = Column(EncryptedText, nullable=False)
    responsibilities = Column(EncryptedText, nullable=True)
    is_internship = Column(Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "lawpersonnel_email": self.lawpersonnel_email,
            "organization_name": self.organization_name,
            "lawpersonnel_type": self.lawpersonnel_type,
            "is_current": self.is_current,
            "position": self.position,
            "duration": self.duration,
            "responsibilities": self.responsibilities,
            "is_internship": self.is_internship,
        }

    def __repr__(self):
        return f"<LawPersonnelExperiences(uuid={self.uuid}, lawpersonnel_email={self.lawpersonnel_email}, organization_name={self.organization_name}, lawpersonnel_type={self.lawpersonnel_type}, is_current={self.is_current}, position={self.position}, duration={self.duration}, responsibilities={self.responsibilities}, is_internship={self.is_internship})>"

class LawPersonnelVerificationDocs(Base):
    __tablename__ = "lawpersonnel_verification_docs"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawpersonnel_type = Column(EncryptedText, nullable=False)
    lawpersonnel_email = Column(EncryptedText, nullable=False, index=True)
    professional_license = Column(EncryptedText, nullable=True)
    government_id = Column(EncryptedText, nullable=False)
    government_id_type = Column(EncryptedText, nullable=False)
    address_document = Column(EncryptedText, nullable=True)
    bank_account = Column(EncryptedText, nullable=True)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "lawpersonnel_type": self.lawpersonnel_type,
            "lawpersonnel_email": self.lawpersonnel_email,
            "professional_license": self.professional_license,
            "government_id": self.government_id,
            "government_id_type": self.government_id_type,
            "address_document": self.address_document,
            "bank_account": self.bank_account,
        }

    def __repr__(self):
        return f"<LawPersonnelVerificationDocs(uuid={self.uuid}, lawpersonnel_type={self.lawpersonnel_type}, lawpersonnel_email={self.lawpersonnel_email}, professional_license={self.professional_license}, government_id={self.government_id}, government_id_type={self.government_id_type}, address_document={self.address_document}, bank_account={self.bank_account})>"

class UserTracking(Base):
    __tablename__ = "user_tracking"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    login_date = Column(Date, nullable=False, server_default=func.now())
    login_email = Column(EncryptedText, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "login_date": self.login_date,
            "login_email": self.login_email,
        }

    def __repr__(self):
        return f"<UserTracking(uuid={self.uuid}, login_date={self.login_date}, login_email={self.login_email})>"

class Connection:
    def __init__(self, database_actor="postgresql"):
        self.connection_string = f"""{database_actor}://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}"""
        self.engine = create_engine(self.connection_string)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

class Functions:
    db = Connection()
    Session = db.SessionLocal

    def get_immigrant(self, parameter: Union[EmailStr, str]) -> Immigrants:
        db = self.Session()
        if "@" in parameter:
            user = (
                db.query(Immigrants)
                .filter(Immigrants.email == parameter.lower())
                .first()
            )
        else:
            user = (
                db.query(Immigrants)
                .filter(Immigrants.username == parameter.lower())
                .first()
            )
        db.close()
        return user

    def get_lawpersonnel(self, parameter: Union[EmailStr, str]) -> LawPersonnel:
        db = self.Session()
        if "@" in parameter:
            lawpersonnel = (
                db.query(LawPersonnel)
                .filter(LawPersonnel.email == parameter.lower())
                .first()
            )
        else:
            lawpersonnel = (
                db.query(LawPersonnel)
                .filter(LawPersonnel.username == parameter.lower())
                .first()
            )
        db.close()
        return lawpersonnel

    def get_external_lawyer(self, parameter: Union[EmailStr, str]) -> ExternalLawyer:
        db = self.Session()
        if "@" in parameter:
            external_lawyer = (
                db.query(ExternalLawyer)
                .filter(ExternalLawyer.email == parameter.lower())
                .first()
            )
        else:
            external_lawyer = (
                db.query(ExternalLawyer)
                .filter(ExternalLawyer.username == parameter.lower())
                .first()
            )
        db.close()
        return external_lawyer

    def update_lawyer_stat(self, lawyer_email: EmailStr, stat_type: str) -> None:
        db = self.Session()
        today = date.today()
        lawyer_stat = (
            db.query(LawyerStats)
            .filter(
                LawyerStats.lawyer_email == lawyer_email.lower(),
                LawyerStats.stat_type == stat_type,
                LawyerStats.stat_date == today,
            )
            .first()
        )
        if lawyer_stat:
            lawyer_stat.stat_val = lawyer_stat.stat_val + 1
        else:
            lawyer_stat = LawyerStats(
                lawyer_email=lawyer_email.lower(),
                stat_date=today,
                stat_type=stat_type,
            )
            db.add(lawyer_stat)
        db.commit()
        db.close()

    def update_user_profile_pic(
        self, user_email: EmailStr, profile_pic_url: str
    ) -> None:
        db = self.Session()
        user = db.query(Immigrants).filter(Immigrants.email == user_email.lower()).first()
        if user:
            user.profile_pic = profile_pic_url
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(status_code=404, detail="User not found")
        db.close()

    def generate_immigrant_username(self, immigrant_email: EmailStr) -> str:
        db = self.Session()
        old_username = username = (
            f"{immigrant_email.split('@')[0]}".replace("_", "").replace(".", "").lower()
        )
        existing_usernames = [user.username for user in db.query(Immigrants).all() if user]
        while username in existing_usernames:
            username = f"{old_username}{randint(1000, 9999)}"

        return username

    def generate_lawpersonnel_username(self, lawpersonnel_email: EmailStr) -> str:
        db = self.Session()
        old_username = username = (
            f"{lawpersonnel_email.split('@')[0]}".replace("_", "")
            .replace(".", "")
            .lower()
        )
        existing_usernames = [user.username for user in db.query(LawPersonnel).all()]
        while username in existing_usernames:
            username = f"{old_username}{randint(1000, 9999)}"

        return username

    def reduce_user_limit(self, user_email: EmailStr) -> None:
        db = self.Session()
        user = (
            db.query(Immigrants).filter(Immigrants.email == user_email.lower()).first()
        )
        if user:
            if user.subscription_type.lower() != "enterprise":
                user.chat_limit -= 1
            db.commit()
        db.close()

    def add_lawpersonnel_experiences(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_type: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
        experiences: list[dict[str, Union[str, bool]]],
    ) -> None:
        db = self.Session()
        for experience in experiences:
            new_experience = LawPersonnelExperiences(
                lawpersonnel_email=lawpersonnel_email.lower(),
                is_current=(
                    experience["is_current"] if "is_current" in experience else False
                ),
                organization_name=experience["organization_name"],
                lawpersonnel_type=lawpersonnel_type.lower(),
                position=experience["position"],
                duration=experience["duration"],
                responsibilities=experience["responsibilities"],
                is_internship=experience["is_internship"],
            )
            db.add(new_experience)

        db.commit()
        db.close()

    def add_lawpersonnel_certificates(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_type: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
        certificates: list[dict[str, Union[str, bool]]],
    ) -> None:
        db = self.Session()
        for certificate in certificates:
            new_certificate = LawPersonnelCertificates(
                lawpersonnel_email=lawpersonnel_email.lower(),
                issuing_organization=certificate["issuing_organization"],
                lawpersonnel_type=lawpersonnel_type.lower(),
                certificate_name=certificate["certificate_name"],
                date_issued=certificate["date_issued"],
                expiry_date=(
                    certificate["expiry_date"] if "expiry_date" in certificate else None
                ),
                certificate_url=certificate["certificate_url"],
                is_professional=(
                    certificate["is_professional"]
                    if "is_professional" in certificate
                    else None
                ),
            )
            db.add(new_certificate)

        db.commit()
        db.close()

    def add_lawpersonnel_info(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_type: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
        experiences: list[dict[str, Union[str, bool]]],
        certificates: list[dict[str, Union[str, bool]]],
    ) -> None:
        self.add_lawpersonnel_experiences(
            lawpersonnel_email, lawpersonnel_type, experiences
        )
        self.add_lawpersonnel_certificates(
            lawpersonnel_email, lawpersonnel_type, certificates
        )

    def delete_lawpersonnel_info(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_type: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
    ):
        db = self.Session()
        experiences = (
            db.query(LawPersonnelExperiences)
            .filter(
                LawPersonnelExperiences.lawpersonnel_email
                == lawpersonnel_email.lower(),
                LawPersonnelExperiences.lawpersonnel_type == lawpersonnel_type.lower(),
            )
            .delete(synchronize_session=False)
        )
        certificates = (
            db.query(LawPersonnelCertificates)
            .filter(
                LawPersonnelCertificates.lawpersonnel_email
                == lawpersonnel_email.lower(),
                LawPersonnelCertificates.lawpersonnel_type == lawpersonnel_type.lower(),
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        db.close()

    def get_lawpersonnel_experiences(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_type: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
    ) -> list[dict[str, Union[str, bool]]]:
        db = self.Session()
        experiences = (
            db.query(LawPersonnelExperiences)
            .filter(
                LawPersonnelExperiences.lawpersonnel_email
                == lawpersonnel_email.lower(),
                LawPersonnelExperiences.lawpersonnel_type == lawpersonnel_type.lower(),
            )
            .all()
        )
        result = []
        if experiences:
            for experience in experiences:
                result.append(
                    {
                        "organization_name": experience.organization_name,
                        "position": experience.position,
                        "duration": experience.duration,
                        "responsibilities": experience.responsibilities,
                        "is_internship": experience.is_internship,
                    }
                )
        db.close()
        return result

    def get_lawpersonnel_certificates(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_type: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
    ) -> list[dict[str, Union[str, bool]]]:
        db = self.Session()
        certificates = (
            db.query(LawPersonnelCertificates)
            .filter(
                LawPersonnelCertificates.lawpersonnel_email
                == lawpersonnel_email.lower(),
                LawPersonnelCertificates.lawpersonnel_type == lawpersonnel_type.lower(),
            )
            .all()
        )
        result = []
        if certificates:
            for certificate in certificates:
                result.append(
                    {
                        "certificate_name": certificate.certificate_name,
                        "issuing_organization": certificate.issuing_organization,
                        "date_issued": certificate.date_issued,
                        "expiry_date": certificate.expiry_date,
                        "certificate_url": certificate.certificate_url,
                    }
                )
        db.close()
        return result

    def add_lawpersonnel_verification_items(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_type: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
        verification_items: dict[str, Union[str, list[str]]],
    ) -> None:
        db = self.Session()
        new_verification = LawPersonnelVerificationDocs(
            lawpersonnel_type=lawpersonnel_type.lower(),
            lawpersonnel_email=lawpersonnel_email.lower(),
            professional_license=verification_items["professional_licenses"],
            government_id=verification_items["government_ids"],
            government_id_type=verification_items["government_id_types"],
            address_document=verification_items["address_documents"],
            bank_account=verification_items["bank_accounts"],
        )
        db.add(new_verification)

        db.commit()
        db.close()

    def delete_lawpersonnel_verification_items(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_type: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
    ) -> None:
        db = self.Session()
        verification_items = (
            db.query(LawPersonnelVerificationDocs)
            .filter(
                LawPersonnelVerificationDocs.lawpersonnel_email
                == lawpersonnel_email.lower(),
                LawPersonnelVerificationDocs.lawpersonnel_type
                == lawpersonnel_type.lower(),
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        db.close()

    def get_lawpersonnel_verification_items(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_type: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
    ) -> list[dict[str, Union[str, list[str]]]]:
        db = self.Session()
        verification_items = db.query(LawPersonnelVerificationDocs).filter(
            LawPersonnelVerificationDocs.lawpersonnel_email
            == lawpersonnel_email.lower(),
            LawPersonnelVerificationDocs.lawpersonnel_type == lawpersonnel_type.lower(),
        )
        result = []
        if verification_items:
            for verification in verification_items:
                result.append(
                    {
                        "professional_license": verification.professional_license,
                        "government_id": verification.government_id,
                        "government_id_type": verification.government_id_type,
                        "address_document": verification.address_document,
                        "bank_account": verification.bank_account,
                    }
                )

        db.close()
        return result

    def update_lawyer_stat(self, lawyer_email: EmailStr, stat_type: str) -> None:
        db = self.Session()
        today = date.today()
        lawyer_stat = (
            db.query(LawyerStats)
            .filter(
                LawyerStats.lawyer_email == lawyer_email.lower(),
                LawyerStats.stat_type == stat_type,
                LawyerStats.stat_date == today,
            )
            .first()
        )
        if lawyer_stat:
            lawyer_stat.stat_val = lawyer_stat.stat_val + 1
        else:
            lawyer_stat = LawyerStats(
                lawyer_email=lawyer_email.lower(),
                stat_date=today,
                stat_type=stat_type,
            )
            db.add(lawyer_stat)
        db.commit()
        db.close()

    def get_lawyer_stat_nums(self, lawyer_email: EmailStr, stat_type: str) -> list[int]:
        db = self.Session()
        today = date.today()
        date_ranges = [
            (today - timedelta(days=6), today),
            (today - timedelta(days=13), today - timedelta(days=7)),
        ]
        growth = [0, 0]
        for i, (start, end) in enumerate(date_ranges):
            total_sum = 0
            stats = (
                db.query(LawyerStats)
                .filter(
                    LawyerStats.lawyer_email == lawyer_email.lower(),
                    LawyerStats.stat_type == stat_type,
                    LawyerStats.stat_date >= start,
                    LawyerStats.stat_date <= end,
                )
                .all()
            )
            if stats:
                for stat in stats:
                    total_sum += stat.stat_val

            growth[i] = total_sum

        db.close()
        return growth

    def get_lawyer_stats(
        self, lawyer_email: EmailStr, stat_type: str
    ) -> list[dict[str, Union[str, int, date]]]:
        db = self.Session()
        lawyer_stats = (
            db.query(LawyerStats)
            .filter(
                LawyerStats.lawyer_email == lawyer_email.lower(),
                LawyerStats.stat_type == stat_type,
            )
            .all()
        )
        result = []
        for stat in lawyer_stats:
            result.append({"date": stat.stat_date, "stat": stat.stat_val})
        return result

    def add_user_tracking(self, user_email: EmailStr) -> None:
        db = self.Session()
        today = datetime.now()
        user_tracking = (
            db.query(UserTracking)
            .filter(
                UserTracking.login_date == today,
                UserTracking.login_email == user_email.lower(),
            )
            .first()
        )
        if not user_tracking:
            new_user_tracking = UserTracking(
                login_date=today, login_email=user_email.lower()
            )
            db.add(new_user_tracking)
            db.commit()

        db.close()

    def update_immigrant_kyc(
        self, immigrant_email: EmailStr, kyc_details: dict[str, Any]
    ) -> None:
        db = self.Session()
        immigrant_kyc = (
            db.query(ImmigrantKYC)
            .filter(ImmigrantKYC.immigrant_email == immigrant_email.lower())
            .first()
        )
        if immigrant_kyc:
            immigrant_kyc.kyc_details = kyc_details
            db.commit()
            db.refresh(immigrant_kyc)
        else:
            new_immigrant_kyc = ImmigrantKYC(
                immigrant_email=immigrant_email.lower(), kyc_details=kyc_details
            )
            db.add(new_immigrant_kyc)
            db.commit()
        db.close()

    def retrieve_immigrant_kyc(self, immigrant_email: EmailStr) -> dict[str, Any]:
        db = self.Session()
        immigrant_kyc = (
            db.query(ImmigrantKYC)
            .filter(ImmigrantKYC.immigrant_email == immigrant_email.lower())
            .first()
        )
        kyc_details = {}
        if immigrant_kyc:
            kyc_details = immigrant_kyc.kyc_details

        db.close()
        return kyc_details

    def delete_immigrant_kyc(self, immigrant_email: EmailStr) -> None:
        db = self.Session()
        immigrant_kyc = (
            db.query(ImmigrantKYC)
            .filter(ImmigrantKYC.immigrant_email == immigrant_email.lower())
            .first()
        )
        if immigrant_kyc:
            db.delete(immigrant_kyc)
            db.commit()

        db.close()

    def add_new_user(
        self,
        username: str,
        email: EmailStr,
        first_name: str,
        full_legal_name: str,
        last_name: str = None,
        location: str = None,
        password: str = None,
        profile_pic_url: str = "https://doloreschatbucket.s3.us-east-2.amazonaws.com/icons/users/user.png",
        data_collection: bool = True,
        receive_emails: bool = True,
        contact_number: str = None,
        date_of_birth: str = None,
    ) -> None:
        db = self.Session()
        user = self.get_user(email)
        if not user:
            user = Immigrants(
                username=username,
                email=email.lower(),
                first_name=first_name,
                last_name=last_name,
                full_legal_name=full_legal_name,
                location=location,
                password=password,
                profile_pic=profile_pic_url,
                data_collection=data_collection,
                receive_emails=receive_emails,
                contact_number=contact_number,
                date_of_birth=date_of_birth,
            )
            db.add(user)
            db.commit()
        db.close()

    def update_user_subscription(
        self,
        email: EmailStr,
        subscription_type: Literal["free", "pay", "plus", "enterprise"],
    ) -> None:
        db = self.Session()
        user = db.query(Immigrants).filter(Immigrants.email == email).first()
        if user:
            if subscription_type != "free":
                if subscription_type == "pay":
                    user.chat_limit += 10
                else:
                    user.chat_limit = math.inf
            elif user.subscription_type not in ["free", "pay"]:
                user.chat_limit = 10

            user.subscription_type = subscription_type
            db.commit()
            db.refresh(user)
        db.close()

    def update_lawpersonnel_subscription(
        self,
        email: EmailStr,
        subscription_type: Literal["new", "lawyer", "nonlawyer", "clinic"],
    ) -> None:
        db = self.Session()
        lawpersonnel = (
            db.query(LawPersonnel).filter(LawPersonnel.email == email).first()
        )
        if lawpersonnel:
            lawpersonnel.subscription_tier = subscription_type
            db.commit()
            db.refresh(lawpersonnel)
        db.close()

    def remove_external_lawyer(self, email: EmailStr) -> None:
        db = self.Session()
        external_lawyer = self.get_external_lawyer(email)
        if external_lawyer:
            db.delete(external_lawyer)
            db.commit()
        db.close()

    def add_new_lawpersonnel(
        self,
        personnel_data: dict[
            str, Union[EmailStr, str, bool, dict[str, Union[str, bool]]]
        ],
    ) -> None:
        db = self.Session()
        new_personnel = LawPersonnel(
            email=personnel_data["email"].lower(),
            firstName=personnel_data["firstName"],
            lastName=personnel_data["lastName"],
            full_legal_name=f"{personnel_data['firstName']} {personnel_data['lastName']}".strip(),
            username=personnel_data["username"],
            profile_picture=personnel_data["profile_picture"],
            professional_address=personnel_data["professional_address"],
            date_of_birth=personnel_data["date_of_birth"],
            contact_number=personnel_data["contact_number"],
            password=personnel_data["password"],
            authorize_verification=personnel_data["authorize_verification"],
            consent_data_collection=personnel_data["consent_data_collection"],
            receive_emails=personnel_data["receive_emails"],
            personnel_type=personnel_data["personnel_type"],
            law_firm_name=personnel_data["law_firm_name"],
            specialty=personnel_data["specialty"],
            experience=personnel_data["experience"],
            details=personnel_data["details"],
        )
        db.add(new_personnel)
        db.commit()
        db.close()

    def delete_lawpersonnel(self, email: EmailStr) -> None:
        db = self.Session()
        personnel = (
            db.query(LawPersonnel).filter(LawPersonnel.email == email.lower()).first()
        )
        if personnel:
            db.delete(personnel)
            db.commit()

        db.close()

    def verify_lawpersonnel(self, email: EmailStr) -> None:
        db = self.Session()
        personnel = (
            db.query(LawPersonnel).filter(LawPersonnel.email == email.lower()).first()
        )
        if personnel:
            personnel.verified = True
            db.commit()
            db.refresh(personnel)
        db.close()

    def add_user_verification(self, email: EmailStr, verification_code: str) -> None:
        db = self.Session()
        exist_user = (
            db.query(UsersVerification)
            .filter(UsersVerification.email == email.lower())
            .first()
        )
        if exist_user:
            exist_user.verification_code = verification_code
            db.commit()
        else:
            user_verification = UsersVerification(
                email=email.lower(), verification_code=verification_code
            )
            db.add(user_verification)
            db.commit()
        db.close()

    def retrieve_user_verification(self, email: EmailStr) -> Union[str, None]:
        db = self.Session()
        user_verification = (
            db.query(UsersVerification)
            .filter(UsersVerification.email == email.lower())
            .first()
        )
        verification_code = None
        if user_verification:
            verification_code = user_verification.verification_code
        db.close()
        return verification_code

    def delete_user_verification(self, email: EmailStr) -> None:
        db = self.Session()
        user_verification = (
            db.query(UsersVerification)
            .filter(UsersVerification.email == email.lower())
            .first()
        )
        if user_verification:
            db.delete(user_verification)
            db.commit()
        db.close()

    def update_user_receipt_number(
        self, email_id: EmailStr, receipt_number: str
    ) -> None:
        db = self.Session()
        user = db.query(Immigrants).filter(Immigrants.email == email_id.lower()).first()
        if user:
            user.receipt_number = receipt_number
            db.commit()
        db.close()

    def add_notification(
        self,
        receiver: EmailStr,
        sender: EmailStr,
        type: Literal[
            "cases",
            "tasks",
            "connection",
            "kyc",
            "forms",
            "teams",
            "lawyer_chat",
            "intake",
            "case_payment",
        ],
        content: str,
        target_id: dict[str, Any],
        one_time: bool = False,
        created_at: datetime = None,
    ):
        db = self.Session()
        if created_at is None:
            notification_alert = NotificationAlerts(
                receiver=receiver.lower(),
                sender=sender.lower(),
                type=type,
                content=content,
                target_id=target_id,
                one_time=one_time,
            )
            db.add(notification_alert)

        if type == "kyc":
            notification_alert = (
                db.query(NotificationAlerts)
                .filter(
                    NotificationAlerts.receiver == receiver.lower(),
                    NotificationAlerts.type == type,
                    NotificationAlerts.target_id == target_id,
                )
                .first()
            )
            if notification_alert:
                notification_alert.update_created_at()
                db.commit()
        else:
            notification_alert = NotificationAlerts(
                receiver=receiver.lower(),
                sender=sender.lower(),
                type=type,
                content=content,
                target_id=target_id,
                one_time=one_time,
                created_at=created_at,
            )
            db.add(notification_alert)

        db.commit()

    def read_notification(self, notification_id: str) -> dict[str, Union[bool, str]]:
        db = self.Session()
        notification_alert = (
            db.query(NotificationAlerts)
            .filter(NotificationAlerts.id == notification_id)
            .first()
        )
        if notification_alert:
            notification_alert.seen = True
            db.commit()
            return {
                "status_change": True,
                "comment": f"Notification #{notification_id} marked as read",
            }
        return {"status_change": False, "comment": "Invalid notification id"}

    def read_allNotifications(self, email: EmailStr) -> dict[str, Union[bool, str]]:
        db = self.Session()
        all_notifications = (
            db.query(NotificationAlerts)
            .filter(
                NotificationAlerts.receiver == email.lower(),
                NotificationAlerts.seen == False,
            )
            .all()
        )
        if all_notifications:
            for notification in all_notifications:
                notification.seen = True
            db.commit()
            return {"read_status": True, "comment": "Marked all notifications as read"}
        return {"read_status": False, "comment": "No unread notifications found"}

    def getNotification_timestamp(self, created_timestamp: datetime) -> str:
        current_time = datetime.now()
        if created_timestamp.date() != current_time.date():
            formatted_date = created_timestamp.strftime("%d %B %Y")
            time_display = formatted_date
        else:
            time_diff = current_time - created_timestamp
            total_seconds = time_diff.total_seconds()

            if total_seconds < 60:
                seconds = round(total_seconds)
                time_display = f"{seconds}s ago"
            elif total_seconds < 3600:
                minutes = round(total_seconds / 60)
                time_display = f"{minutes}m ago"
            else:
                hours = round(total_seconds / 3600)
                time_display = f"{hours}h ago"

        return time_display

    def get_notifications(
        self, email: EmailStr
    ) -> dict[str, Union[list[dict[str, Union[str, bool, dict[str, str]]]], int]]:
        db = self.Session()
        all_notifications = (
            db.query(NotificationAlerts)
            .filter(NotificationAlerts.receiver == email.lower())
            .all()
        )
        now = datetime.now() + timedelta(days=1)
        returnVal = {"notifications": [], "unread": 0}
        if all_notifications:
            for notification in all_notifications:
                if notification.created_at < now:
                    notif = {
                        "id": notification.id,
                        "type": notification.type,
                        "content": notification.content,
                        "target_id": notification.target_id,
                        "created_stamp": self.getNotification_timestamp(
                            notification.created_at
                        ),
                        "seen": notification.seen,
                    }
                    if notification.one_time == True and notification.seen == False:
                        returnVal["unread"] += 1
                        returnVal["notifications"].append(notif)
                    elif notification.one_time == False:
                        if notification.seen == False:
                            returnVal["unread"] += 1
                        returnVal["notifications"].append(notif)

        return returnVal

    def delete_notification(
        self,
        email: EmailStr,
        type: str = Literal[
            "cases",
            "tasks",
            "connection",
            "kyc",
            "forms",
            "teams",
            "lawyer_chat",
            "intake",
            "case_payment",
        ],
        id: str = None,
        data: dict[str, Any] = None,
        content: str = None,
    ):
        db = self.Session()
        notifications = (
            db.query(NotificationAlerts)
            .filter(
                NotificationAlerts.receiver == email.lower(),
                NotificationAlerts.type == type,
            )
            .all()
        )
        if notifications:
            for notification in notifications:
                if id is not None:
                    if notification.id == id:
                        db.delete(notification)
                        db.commit()
                    return "Deleted specific notification"
                elif data is not None:
                    if notification.target_id == data:
                        db.delete(notification)
                        db.commit()
                    return "Deleted specific notification"
                elif content is not None:
                    if notification.content == content:
                        db.delete(notification)
                        db.commit()
                else:
                    return "Cannot delete specific notification"
        else:
            return f"No notifications found for this user of type {type}"

    def retrieve_messageCount(
        self,
        email: EmailStr,
        type: Literal[
            "cases",
            "tasks",
            "connection",
            "kyc",
            "forms",
            "teams",
            "lawyer_chat",
            "intake",
            "case_payment",
        ],
        sender: EmailStr,
    ):
        db = self.Session()
        notification = (
            db.query(NotificationAlerts)
            .filter(
                NotificationAlerts.receiver == email.lower(),
                NotificationAlerts.type == type,
                NotificationAlerts.sender == sender.lower(),
            )
            .first()
        )
        count = 0
        notification_id = None
        message_string = "a new message"
        if notification:
            notification_id = notification.id
            if "a new message" in notification.content:
                count = 1
                message_string = " new messages"
            else:
                split_string = notification.content.split(" new messages")[0]
                message_string = " new messages"
                match = re.search(r"\d+", split_string)
                if match:
                    count = int(match.group())
        return count, message_string, notification_id

    def remove_referred_notification(self, immigrant_email: EmailStr) -> None:
        db = self.Session()

        notification_alerts = (
            db.query(NotificationAlerts)
            .filter(
                NotificationAlerts.sender == immigrant_email.lower(),
                NotificationAlerts.type == "connection",
            )
            .all()
        )
        if notification_alerts:
            for alert in notification_alerts:
                if "Refered user" in alert.content and alert.target_id == {}:
                    db.delete(alert)
            db.commit()
        db.close()

    def retrieve_all_notification_ids(self) -> list[str]:
        db = self.Session()
        all_notifications = db.query(NotificationAlerts.id).all()
        if all_notifications:
            db.close()
            return [notif[0] for notif in all_notifications]
        db.close()
        return []