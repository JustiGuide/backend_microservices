import asyncio
import base64
import json
import os
from typing import Any, Union, Literal
from fastapi import WebSocketDisconnect
from pydantic import EmailStr
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm.attributes import flag_modified
from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    Column,
    Float,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    create_engine,
    func,
)

from encryptor import EncryptedText, Encrypt
from datetime import datetime, timezone, timedelta

load_dotenv()


Base = declarative_base()
class TwilioContext(Base):
    __tablename__ = "twilio_context"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    added_date = Column(Date, nullable=False, server_default=func.now())
    user_number = Column(EncryptedText, nullable=False, index=True)
    user_context = Column(EncryptedText, nullable=False)
    ai_context = Column(EncryptedText, nullable=False)
    contact_method = Column(Text, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "added_date": self.added_date,
            "user_number": self.user_number,
            "user_context": self.user_context,
            "ai_context": self.ai_context,
            "contact_method": self.contact_method,
        }

    def __repr__(self):
        return f"<TwilioContext(uuid={self.uuid}, added_date={self.added_date}, user_number={self.user_number}, user_context={self.user_context}, ai_context={self.ai_context}, contact_method={self.contact_method})>"


class TwilioInteractions(Base):
    __tablename__ = "twilio_interactions"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    added_date = Column(Date, nullable=False, server_default=func.now())
    user_number = Column(EncryptedText, nullable=False)
    contact_reason = Column(EncryptedText, nullable=False)
    contact_method = Column(Text, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "added_date": self.added_date,
            "user_number": self.user_number,
            "contact_reason": self.contact_reason,
            "contact_method": self.contact_method,
        }

    def __repr__(self):
        return f"<TwilioInteractions(uuid={self.uuid}, added_date={self.added_date}, user_number={self.user_number}, contact_reason={self.contact_reason}, contact_method={self.contact_method})>"


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
        # TODO: Connect with User Management
        # db = self.Session()
        # if "@" in parameter:
        #     user = (
        #         db.query(Immigrants)
        #         .filter(Immigrants.email == parameter.lower())
        #         .first()
        #     )
        # else:
        #     user = (
        #         db.query(Immigrants)
        #         .filter(Immigrants.username == parameter.lower())
        #         .first()
        #     )
        # db.close()
        # return user
        pass

    def get_lawpersonnel(self, parameter: Union[EmailStr, str]) -> LawPersonnel:
        # TODO: Connect with User Management
        # db = self.Session()
        # if "@" in parameter:
        #     lawpersonnel = (
        #         db.query(LawPersonnel)
        #         .filter(LawPersonnel.email == parameter.lower())
        #         .first()
        #     )
        # else:
        #     lawpersonnel = (
        #         db.query(LawPersonnel)
        #         .filter(LawPersonnel.username == parameter.lower())
        #         .first()
        #     )
        # db.close()
        # return lawpersonnel
        pass

    def get_external_lawyer(self, parameter: Union[EmailStr, str]) -> ExternalLawyer:
        # TODO: Connect with User Management
        pass

    def add_twilio_interaction(
        self,
        user_number: str,
        contact_reason: str,
        contact_method: str = Literal["call", "text", "whatsapp"],
    ) -> None:
        db = self.Session()
        new_interaction = TwilioInteractions(
            user_number=user_number,
            contact_reason=contact_reason,
            contact_method=contact_method,
        )
        db.add(new_interaction)
        db.commit()
        db.close()

    def update_twilio_context(
        self,
        user_number: str,
        user_context: str,
        ai_context: str,
        contact_method: str = Literal["call", "text", "whatsapp"],
    ) -> None:
        db = self.Session()
        today = datetime.now(timezone.utc)
        start_date = today - timedelta(days=7)
        twilio_context = (
            db.query(TwilioContext)
            .filter(
                TwilioContext.user_number == user_number,
                TwilioContext.contact_method == contact_method,
                TwilioContext.added_date >= start_date,
            )
            .order_by(TwilioContext.added_date.desc())
            .first()
        )
        if twilio_context:
            twilio_context.user_context = user_context
            twilio_context.ai_context = ai_context
            db.commit()
            db.refresh(twilio_context)
        else:
            new_twilio_context = TwilioContext(
                user_number=user_number,
                user_context=user_context,
                ai_context=ai_context,
                contact_method=contact_method,
            )
            db.add(new_twilio_context)
            db.commit()
        db.close()

    def retrieve_twilio_context(
        self,
        user_number: str,
        contact_method: str = Literal["call", "text", "whatsapp"],
    ) -> tuple[str, str]:
        db = self.Session()
        today = datetime.now(timezone.utc)
        start_date = today - timedelta(days=7)
        user_context = None
        ai_context = None
        twilio_context = (
            db.query(TwilioContext)
            .filter(
                TwilioContext.user_number == user_number,
                TwilioContext.contact_method == contact_method,
                TwilioContext.added_date >= start_date,
            )
            .order_by(TwilioContext.added_date.desc())
            .first()
        )
        if twilio_context:
            user_context = twilio_context.user_context
            ai_context = twilio_context.ai_context

        db.close()
        return user_context, ai_context

    def update_twilio_conversation(self, 
        user_num: str,
        messages: list[str],
        comm_type: Literal["call", "text", "whatsapp"],
        user_input: str,
        user_context: str,
        answer: str,
        ai_context: str,
        method: Literal["call", "text", "whatsapp"],
    ) -> bool:
        # TODO: connect with ai agents
        pass

    def update_twilio_reason(
        self,
        user_num: str,
        messages: list[str],
        comm_type: str = Literal["call", "text", "whatsapp"],
    ) -> bool:
        # TODO: connect with ai agents
        pass

    def add_user_verification(self, email: EmailStr, verification_code: str) -> None:
        # db = self.Session()
        # exist_user = (
        #     db.query(UsersVerification)
        #     .filter(UsersVerification.email == email.lower())
        #     .first()
        # )
        # if exist_user:
        #     exist_user.verification_code = verification_code
        #     db.commit()
        # else:
        #     user_verification = UsersVerification(
        #         email=email.lower(), verification_code=verification_code
        #     )
        #     db.add(user_verification)
        #     db.commit()
        # db.close()
        # TODO: Connect with user management
        pass

    def add_invitation(
        self,
        invited_type: Literal[
            "invited_client",
            "pending_case",
            "pending_client",
            "invited_external_lawyer",
            "invited_to_case",
            "invited_to_team",
            "refered_user",
        ],
        invitee_email: EmailStr,
        invited_email: EmailStr,
        case_type: Literal[
            "nonimmigrant_worker",
            "employment_auth",
            "alien_rel",
            "asylum_removal",
            "naturalization",
        ] = None,
        client_number: str = None,
        client_address: str = None,
        case_id: str = None,
        member_role: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"] = None,
        member_permissions: Literal["Admin", "Commenter", "Viewer"] = None,
        case_name: str = None,
        case_description: str = None,
        assignees: list[EmailStr] = None,
    ) -> bool:
        # db = self.Session()
        # exist_invitation = (
        #     db.query(Invitations)
        #     .filter(
        #         Invitations.invited_email == invited_email.lower(),
        #         Invitations.invited_type == invited_type,
        #         Invitations.invitee_email == invitee_email,
        #     )
        #     .first()
        # )
        # invitation_map = {
        #     "invited_client": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         case_type=case_type,
        #     ),
        #     "pending_case": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         case_id=case_id,
        #         client_number=client_number,
        #         client_address=client_address,
        #         case_name=case_name,
        #         case_description=case_description,
        #         case_type=case_type,
        #         assignees=assignees,
        #     ),
        #     "pending_client": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         client_number=client_number,
        #         client_address=client_address,
        #         case_type=case_type,
        #     ),
        #     "invited_external_lawyer": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         client_number=client_number,
        #         client_address=client_address,
        #         case_type=case_type,
        #     ),
        #     "invited_to_case": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         member_role=member_role,
        #         member_permissions=member_permissions,
        #         case_id=case_id,
        #     ),
        #     "invited_to_team": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         member_role=member_role,
        #         member_permissions=member_permissions,
        #     ),
        #     "refered_user": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #     ),
        # }
        # invite_success = False
        # if not exist_invitation:
        #     new_invitation = invitation_map[invited_type]
        #     db.add(new_invitation)
        #     db.commit()
        #     add_record_to_airtable(new_invitation)
        #     invite_success = True
        # db.close()
        # return invite_success
        # TODO: connect with relationship management
        pass

    def retrieve_clients(self, lawyer_email: EmailStr) -> list[EmailStr]:
        # db = self.Session()
        # all_clients = []
        # clients = (
        #     db.query(AllClients)
        #     .filter(AllClients.lawyer_email == lawyer_email.lower())
        #     .all()
        # )
        # for client in clients:
        #     all_clients.append(client.client_email)

        # db.close()
        # return all_clients
        # TODO: Connect with relationship management
        pass

    def start_password_reset(self, email_id: EmailStr, user_type: Literal["immigrant", "lawpersonnel"]) -> bool:
        # TODO: Connect with user management
        pass