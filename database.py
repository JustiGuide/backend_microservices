import os
from typing import Any, Union, Literal
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
)

# from response_schemas import Task
from encryptor import EncryptedText, Encrypt
from datetime import datetime, timezone
from helpers import Helpers

load_dotenv()

encr = Encrypt()
Base = declarative_base()


class Connection:
    def __init__(self, database_actor="postgresql"):
        self.connection_string = f"""{database_actor}://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}"""
        self.engine = create_engine(self.connection_string)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )


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
    def password(self, plain_password: str):
        self.hashed_password = encr.hash_password(plain_password)

    def verify_password(self, plain_password: str) -> bool:
        return encr.verify_password(plain_password, self.hashed_password)


class ImmigrantAIChat(Base):
    __tablename__ = "immigrant_ai_chat"
    uuid: str = Column(String(7), primary_key=True, default=encr.generate_uuid)
    immigrant_email: EmailStr = Column(EncryptedText, nullable=False, index=True)
    message: str = Column(EncryptedText, nullable=False)
    references: dict[str, list[str]] = Column(EncryptedText, nullable=True)
    sender: str = Column(Text, nullable=False)
    timestamp: datetime = Column(DateTime(timezone=True), nullable=False)
    feedback: str = Column(EncryptedText, nullable=True)
    vote: str = Column(String(10), nullable=True)
    document_urls: list[str] = Column(EncryptedText, nullable=True)

    def to_dict(self) -> dict[str, Union[str, EmailStr, dict, datetime, list]]:
        return {
            "uuid": self.uuid,
            "immigrant_email": self.immigrant_email,
            "message": self.message,
            "references": self.references,
            "sender": self.sender,
            "timestamp": self.timestamp,
            "feedback": self.feedback,
            "vote": self.vote,
            "document_urls": self.document_urls,
        }

    def __repr__(self) -> str:
        return f"<ImmigrantAIChat(uuid={self.uuid}, immigrant_email={self.immigrant_email}, message={self.message}, references={self.references}, sender={self.sender}, timestamp={self.timestamp}, feedback={self.feedback}, vote={self.vote}, document_urls={self.document_urls})>"


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
    def password(self, plain_password: str):
        self.hashed_password = encr.hash_password(plain_password)

    # Password Verification Method
    def verify_password(self, plain_password: str) -> bool:
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
    


class LawPersonnelAIChat(Base):
    __tablename__ = "lawpersonnel_ai_chat"
    uuid: str = Column(String(7), primary_key=True, default=encr.generate_uuid)
    lawpersonnel_email: EmailStr = Column(EncryptedText, nullable=False, index=True)
    message: str = Column(EncryptedText, nullable=False)
    references: dict[str, list[str]] = Column(EncryptedText, nullable=True)
    sender: str = Column(Text, nullable=False)
    timestamp: datetime = Column(DateTime(timezone=True), nullable=False)
    feedback: str = Column(EncryptedText, nullable=True)
    favorite_bool: bool = Column(Boolean, nullable=False, default=False)
    vote: str = Column(String(10), nullable=True)
    document_urls: list[str] = Column(EncryptedText, nullable=True)

    def to_dict(self) -> dict[str, Union[str, EmailStr, dict, datetime, list]]:
        return {
            "uuid": self.uuid,
            "lawpersonnel_email": self.lawpersonnel_email,
            "message": self.message,
            "references": self.references,
            "sender": self.sender,
            "timestamp": self.timestamp,
            "feedback": self.feedback,
            "favorite_bool": self.favorite_bool,
            "vote": self.vote,
            "document_urls": self.document_urls,
        }

    def __repr__(self) -> str:
        return f"<LawPersonnelAIChat(uuid={self.uuid}, lawpersonnel_email={self.lawpersonnel_email}, message={self.message}, references={self.references}, sender={self.sender}, timestamp={self.timestamp}, feedback={self.feedback}, favorite_bool={self.favorite_bool}, vote={self.vote}, document_urls={self.document_urls})>"


class ImmigrantDocuments(Base):
    __tablename__ = "immigrant_documents"
    uuid: str = Column(String(7), primary_key=True, default=encr.generate_uuid)
    immigrant_email: EmailStr = Column(EncryptedText, nullable=False, index=True)
    file_url: str = Column(EncryptedText, nullable=False)
    file_type: str = Column(Text, nullable=False)

    def to_dict(self) -> dict[str, Union[str, EmailStr]]:
        return {
            "uuid": self.uuid,
            "immigrant_email": self.immigrant_email,
            "file_url": self.file_url,
            "file_type": self.file_type,
        }

    def __repr__(self) -> str:
        return f"<ImmigrantDocuments(uuid={self.uuid}, immigrant_email={self.immigrant_email}, file_url={self.file_url}, file_type={self.file_type})>"


class AllFiles(Base):
    __tablename__ = "all_files"
    uuid: str = Column(
        String(7), primary_key=True, nullable=False, default=encr.generate_uuid
    )
    file_name: str = Column(EncryptedText, nullable=False)
    file_url: str = Column(EncryptedText, nullable=False)
    file_type: str = Column(EncryptedText, nullable=False)
    upload_date: datetime.date = Column(
        Date, nullable=False, default=datetime.now(tz=timezone.utc)
    )
    file_size: str = Column(String, nullable=False)
    open_read: bool = Column(Boolean, nullable=False, default=False)
    owner: EmailStr = Column(EncryptedText, nullable=False)
    owner_type: str = Column(EncryptedText, nullable=False)

    def to_dict(self) -> dict[str, Union[str, datetime.date, bool, EmailStr]]:
        return {
            "uuid": self.uuid,
            "file_name": self.file_name,
            "file_url": self.file_url,
            "file_type": self.file_type,
            "upload_date": self.upload_date,
            "file_size": self.file_size,
            "open_read": self.open_read,
            "owner": self.owner,
            "owner_type": self.owner_type,
        }

    def __repr__(self) -> str:
        return f"<AllFiles(uuid={self.uuid}, file_name={self.file_name}, file_url={self.file_url}, file_type={self.file_type}, upload_date={self.upload_date}, file_size={self.file_size}, open_read={self.open_read}, owner={self.owner}, owner_type={self.owner_type})>"


class ApplicationChecklists(Base):
    __tablename__ = "application_checklists"
    uuid: str = Column(String(7), primary_key=True, default=encr.generate_uuid)
    immigrant_email: EmailStr = Column(EncryptedText, nullable=False, index=True)
    form_name: str = Column(EncryptedText, nullable=False)
    checklist_items: list[dict[str, Union[str, list[str]]]] = Column(
        JSON, nullable=False, default=[]
    )
    checklist_checked: bool = Column(Boolean, nullable=False, default=False)

    def to_dict(
        self,
    ) -> dict[str, Union[str, EmailStr, bool, list[dict[str, Union[str, list[str]]]]]]:
        return {
            "uuid": self.uuid,
            "immigrant_email": self.immigrant_email,
            "form_name": self.form_name,
            "checklist_items": self.checklist_items,
            "checklist_checked": self.checklist_checked,
        }

    def __repr__(self) -> str:
        return f"<ApplicationChecklists(uuid={self.uuid}, immigrant_email={self.immigrant_email}, form_name={self.form_name}, checklist_items={self.checklist_items}, checklist_checked={self.checklist_checked})>"


class CompilerDocuments(Base):
    __tablename__ = "compiler_documents"
    uuid: str = Column(String(7), primary_key=True, default=encr.generate_uuid)
    file_name: str = Column(EncryptedText, nullable=False)
    file_url: str = Column(EncryptedText, nullable=False)
    file_type: str = Column(EncryptedText, nullable=False)
    file_size: str = Column(String, nullable=False)
    owner: EmailStr = Column(EncryptedText, nullable=False)
    case_type: str = Column(EncryptedText, nullable=False)
    case_id: str = Column(String(7), nullable=True)
    to_replace: bool = Column(Boolean, nullable=False, default=False)
    verified: bool = Column(Boolean, nullable=False, default=False)
    replace_reasons: str = Column(EncryptedText, nullable=True, default=None)

    def to_dict(self) -> dict[str, Union[str, EmailStr, bool]]:
        return {
            "uuid": self.uuid,
            "file_name": self.file_name,
            "file_url": self.file_url,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "owner": self.owner,
            "case_type": self.case_type,
            "case_id": self.case_id,
            "to_replace": self.to_replace,
            "replace_reasons": self.replace_reasons,
            "verified": self.verified,
        }

    def __repr__(self) -> str:
        return f"<CompilerDocuments(uuid={self.uuid}, file_name={self.file_name}, file_url={self.file_url}, file_type={self.file_type}, file_size={self.file_size}, owner={self.owner}, case_type={self.case_type}, case_id={self.case_id}, to_replace={self.to_replace}, replace_reasons={self.replace_reasons}, verified={self.verified})>"


class AutofillData(Base):
    __tablename__ = "autofill_data"
    uuid: str = Column(String(7), primary_key=True, default=encr.generate_uuid)
    immigrant_username: str = Column(EncryptedText, nullable=False)
    form_name: str = Column(EncryptedText, nullable=False)
    form_data: dict = Column(EncryptedText, nullable=False)
    field_descriptions: dict = Column(EncryptedText, nullable=False)
    immigrant_context: dict = Column(EncryptedText, nullable=False)
    immigrant_rag_context: str = Column(EncryptedText, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Union[str, dict, datetime]]:
        return {
            "uuid": self.uuid,
            "immigrant_username": self.immigrant_username,
            "form_name": self.form_name,
            "form_data": self.form_data,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return f"<AutofillData(uuid={self.uuid}, immigrant_username={self.immigrant_username}, form_name={self.form_name}, form_data={self.form_data}, created_at:{self.created_at})>"


class FluencyProfile(Base):
    __tablename__ = "fluency_profiles"
    uuid: str = Column(String(7), primary_key=True, default=encr.generate_uuid)
    immigrant_email: EmailStr = Column(EncryptedText, index=True, nullable=False)
    interaction_history: list[dict[str, Any]] = Column(JSON, nullable=False, default=[])
    last_session_date: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    overall_fluency_score: float = Column(Float, default=0.0)
    strengths: list = Column(JSON, default=[])
    areas_for_improvement: list = Column(JSON, default=[])

    def to_dict(self) -> dict[str, Union[str, EmailStr, list, datetime]]:
        return {
            "uuid": self.uuid,
            "immigrant_email": self.immigrant_email,
            "interaction_history": self.interaction_history,
            "last_session_date": self.last_session_date,
            "overall_fluency_score": self.overall_fluency_score,
            "strengths": self.strengths,
            "areas_for_improvement": self.areas_for_improvement,
        }

    def __repr__(self):
        return f"<FluencyProfile(uuid={self.uuid}, immigrant_email={self.immigrant_email}, interaction_history={self.interaction_history}, last_session_date={self.last_session_date}, overall_fluency_score={self.overall_fluency_score}, strengths={self.strengths}, areas_for_improvement={self.areas_for_improvement})>"


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


class LawyerRecommendations(Base):
    __tablename__ = "lawyer_recommendations"
    uuid = Column(String(7), primary_key=True, default=encr.generate_uuid)
    client_email = Column(EncryptedText, nullable=False, index=True)
    registered_lawyers = Column(EncryptedText, nullable=False)
    unregistered_lawyers = Column(EncryptedText, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "client_email": self.client_email,
            "registered_lawyers": self.registered_lawyers,
            "unregistered_lawyers": self.unregistered_lawyers,
        }

    def __repr__(self):
        return f"<LawyerRecommendations(uuid={self.uuid}, client_email={self.client_email}, registered_lawyers={self.registered_lawyers}, unregistered_lawyers={self.unregistered_lawyers})>"


class N400Quiz(Base):
    __tablename__ = "n400_quiz"
    uuid: str = Column(String(7), primary_key=True, default=encr.generate_uuid)
    immigrant_email: EmailStr = Column(EncryptedText, nullable=False, index=True)
    quiz_data: list[dict[str, str]] = Column(EncryptedText, nullable=False, default=[])
    start_date: datetime = Column(DateTime(timezone=True), nullable=False)
    quiz_score: int = Column(Integer, nullable=True, default=0)
    quiz_completed: bool = Column(Boolean, nullable=False, default=False)
    end_date: datetime = Column(DateTime(timezone=True), nullable=True)
    old_quiz_data: list[dict[str, str]] = Column(
        EncryptedText, nullable=True, default=[]
    )

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "immigrant_email": self.immigrant_email,
            "quiz_data": self.quiz_data,
            "start_date": self.start_date,
            "quiz_score": self.quiz_score,
            "quiz_completed": self.quiz_completed,
            "end_date": self.end_date,
            "old_quiz_data": self.old_quiz_data,
        }

    def __repr__(self):
        return f"<N400Quiz(uuid={self.uuid}, immigrant_email={self.immigrant_email}, quiz_data={self.quiz_data}, start_date={self.start_date}, quiz_score={self.quiz_score}, quiz_completed={self.quiz_completed}, end_date={self.end_date}, old_quiz_data={self.old_quiz_data})>"


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

    def get_immigrant_kyc(self, parameter: Union[EmailStr, str]) -> dict:
        # TODO: connect with user management
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

    def get_timestamp_from_id(self, message_timestamp: Union[str, int]) -> datetime:
        seconds = int(message_timestamp) / 1000
        return datetime.fromtimestamp(seconds, tz=timezone.utc)

    def get_current_timestamp(self) -> datetime:
        return datetime.now(timezone.utc)

    def store_immigrant_message(
        self,
        immigrant_email: EmailStr,
        sender: str,
        message: str,
        references: dict[str, list[str]] = {},
        message_timestamp: Union[str, int] = None,
        documents: list[str] = [],
    ) -> str:
        db = self.Session()
        if message_timestamp is not None:
            timestamp = self.get_timestamp_from_id(message_timestamp)
        else:
            timestamp = self.get_current_timestamp()
        new_message = ImmigrantAIChat(
            immigrant_email=immigrant_email.lower(),
            message=message,
            references=references,
            sender=sender.lower(),
            timestamp=timestamp,
            document_urls=documents,
        )
        db.add(new_message)
        db.commit()
        message_id = new_message.uuid
        db.close()
        return message_id

    def store_lawpersonnel_message(
        self,
        lawpersonnel_email: EmailStr,
        sender: str,
        message: str,
        references: dict[str, list[str]] = {},
        message_timestamp: Union[str, int] = None,
        documents: list[str] = [],
    ) -> str:
        db = self.Session()
        if message_timestamp is not None:
            timestamp = self.get_timestamp_from_id(message_timestamp)
        else:
            timestamp = self.get_current_timestamp()
        new_message = LawPersonnelAIChat(
            lawpersonnel_email=lawpersonnel_email.lower(),
            message=message,
            references=references,
            sender=sender.lower(),
            timestamp=timestamp,
            document_urls=documents,
        )

        db.add(new_message)
        db.commit()
        message_id = new_message.uuid
        db.close()
        return message_id

    def add_immigrant_filedetails(
        self,
        immigrant_email: EmailStr,
        file_url: str,
        file_type: Literal[
            "ai_chat_files", "forms", "personal_files", "form_details"
        ],
    ) -> None:
        # TODO: Connect with User Management
        # db = self.Session()
        # immigrant_file = ImmigrantDocuments(
        #     immigrant_email=immigrant_email.lower(),
        #     file_url=file_url,
        #     file_type=file_type,
        # )
        # db.add(immigrant_file)
        # db.commit()
        # db.close()
        pass

    def add_lawpersonnel_filedetails(
        self,
        lawpersonnel_email: EmailStr,
        file_url: str,
        file_type: Literal[
            "ai_chat_files", "forms", "personal_files", "form_details"
        ],
    ) -> None:
        # TODO: Connect with User Management
        # db = self.Session()
        # lawpersonnel_file = LawpersonnelDocuments(
        #     lawpersonnel_email=lawpersonnel_email.lower(),
        #     file_url=file_url,
        #     file_type=file_type,
        # )
        # db.add(lawpersonnel_file)
        # db.commit()
        # db.close()
        pass

    def reduce_immigrant_chat_limit(self, immigrant_email: EmailStr) -> None:
        # TODO: Connect with User Management
        # db = self.Session()
        # immigrant = db.query(Immigrants).filter(Immigrants.email == immigrant_email.lower()).first()
        # if immigrant:
        #     if immigrant.subscription_type.lower() != "enterprise":
        #         immigrant.chat_limit -= 1
        #     db.commit()
        # db.close()
        pass

    def add_immigrant_chat_feedback(
        self,
        immigrant_email: EmailStr,
        message_id: str,
        feedback: str,
        vote: Literal["upvote", "downvote"],
    ) -> bool:
        db = self.Session()
        message = (
            db.query(ImmigrantAIChat)
            .filter(
                ImmigrantAIChat.immigrant_email == immigrant_email.lower(),
                ImmigrantAIChat.uuid == message_id,
            )
            .first()
        )
        if message:
            message.feedback = feedback
            message.vote = vote
            db.commit()
            db.refresh(message)
            db.close()
            return True
        db.close()
        return False

    def delete_immigrant_ai_chat(self, immigrant_email: EmailStr):
        db = self.Session()
        db.query(ImmigrantAIChat).filter(
            ImmigrantAIChat.immigrant_email == immigrant_email.lower()
        ).delete(synchronize_session=False)
        db.commit()
        db.close()

    def add_lawpersonnel_chat_feedback(
        self,
        lawpersonnel_email: EmailStr,
        message_id: str,
        feedback: str,
        vote: Literal["upvote", "downvote"],
    ) -> bool:
        db = self.Session()
        message = (
            db.query(LawPersonnelAIChat)
            .filter(
                LawPersonnelAIChat.lawpersonnel_email == lawpersonnel_email.lower(),
                LawPersonnelAIChat.uuid == message_id,
            )
            .first()
        )
        if message:
            message.feedback = feedback
            message.vote = vote
            db.commit()
            db.refresh(message)
            db.close()
            return True
        db.close()
        return False

    def delete_lawpersonnel_ai_chat(self, lawpersonnel_email: EmailStr):
        db = self.Session()
        db.query(LawPersonnelAIChat).filter(
            LawPersonnelAIChat.lawpersonnel_email == lawpersonnel_email.lower()
        ).delete(synchronize_session=False)
        db.commit()
        db.close()

    def delete_lawpersonnel_ai_message(
        self, lawpersonnel_email: EmailStr, message_id: str
    ):
        db = self.Session()
        db.query(LawPersonnelAIChat).filter(
            LawPersonnelAIChat.lawpersonnel_email == lawpersonnel_email.lower(),
            LawPersonnelAIChat.uuid == message_id,
        ).delete(synchronize_session=False)
        db.commit()
        db.close()

    def retrieve_file(self, file_url: str, owner_email: EmailStr = None) -> AllFiles:
        # TODO: Connect with Documents Service (AllFiles)
        pass

    def process_immigrant_messages(
        self, immigrant_email: EmailStr
    ) -> dict[
        str, dict[str, dict[str, Union[str, list[str], dict[str, list[str]], datetime]]]
    ]:
        db = self.Session()
        messages = (
            db.query(ImmigrantAIChat)
            .filter(ImmigrantAIChat.immigrant_email == immigrant_email.lower())
            .all()
        )
        result = {}
        if messages:
            for message in messages:
                if message.sender not in result:
                    result[message.sender] = {}

                new_urls = []
                doc_sizes = []
                for document in message.document_urls:
                    file = self.retrieve_file(document)
                    if file:
                        new_urls.append(
                            f"{os.getenv('BACKEND')}file/{file.uuid}/{file.file_name}"
                        )
                        doc_sizes.append(file.file_size)

                result[message.sender][message.uuid] = {
                    "message": message.message,
                    "references": message.references,
                    "timestamp": message.timestamp,
                    "feedback": message.feedback,
                    "vote": message.vote,
                    "documents": new_urls,
                    "document_sizes": doc_sizes,
                }
        db.close()
        return result

    def process_lawpersonnel_messages(
        self, lawpersonnel_email: EmailStr, starred: bool = False
    ) -> dict[
        str, dict[str, dict[str, Union[str, list[str], dict[str, list[str]], datetime]]]
    ]:
        db = self.Session()
        messages = (
            db.query(LawPersonnelAIChat)
            .filter(LawPersonnelAIChat.lawpersonnel_email == lawpersonnel_email.lower())
            .all()
        )
        result = {}
        if messages:
            for message in messages:
                if message.sender not in result:
                    result[message.sender] = {}

                new_urls = []
                doc_sizes = []
                for document in message.document_urls:
                    file = self.retrieve_file(document)
                    if file:
                        new_urls.append(
                            f"{os.getenv('BACKEND')}file/{file.uuid}/{file.file_name}"
                        )
                        doc_sizes.append(file.file_size)

                message_dictionary = {
                    "message": message.message,
                    "references": message.references,
                    "timestamp": message.timestamp,
                    "feedback": message.feedback,
                    "vote": message.vote,
                    "documents": new_urls,
                    "document_sizes": doc_sizes,
                }

                if not starred or message.favorite_bool:
                    result[message.sender][message.uuid] = message_dictionary
        db.close()
        return result

    def update_lawpersonnel_message_favorite_bool(
        self, lawpersonnel_email: EmailStr, message_id: str, favorite_bool: bool
    ) -> None:
        db = self.Session()
        message = (
            db.query(LawPersonnelAIChat)
            .filter(
                LawPersonnelAIChat.lawpersonnel_email == lawpersonnel_email.lower(),
                LawPersonnelAIChat.uuid == message_id,
            )
            .first()
        )
        if message:
            message.favorite_bool = favorite_bool
            db.commit()
            db.refresh(message)
        db.close()

    def get_application_checklist(
        self, immigrant_email: EmailStr, form_name: str
    ) -> list[dict[str, Union[str, list[str]]]]:
        db = self.Session()
        checklist = (
            db.query(ApplicationChecklists)
            .filter(
                ApplicationChecklists.immigrant_email == immigrant_email,
                ApplicationChecklists.form_name == form_name,
            )
            .first()
        )
        checklist_data = []
        if checklist:
            checklist_data = checklist.checklist_items
        db.close()
        return checklist_data

    def add_application_checklist(
        self,
        immigrant_email: EmailStr,
        form_name: str,
        checklist_items: list[dict[str, Union[str, list[str]]]],
    ) -> None:
        db = self.Session()
        exist_checklist = (
            db.query(ApplicationChecklists)
            .filter(
                ApplicationChecklists.immigrant_email == immigrant_email,
                ApplicationChecklists.form_name == form_name,
            )
            .first()
        )
        if exist_checklist:
            exist_checklist.checklist_items = checklist_items
            db.commit()
            db.close()
        else:
            new_checklist = ApplicationChecklists(
                immigrant_email=immigrant_email,
                form_name=form_name,
                checklist_items=checklist_items,
            )
            db.add(new_checklist)
            db.commit()
            db.close()

    def verify_checked_checklist(
        self, immigrant_email: EmailStr, form_name: str
    ) -> None:
        db = self.Session()
        checklist = (
            db.query(ApplicationChecklists)
            .filter(
                ApplicationChecklists.immigrant_email == immigrant_email,
                ApplicationChecklists.form_name == form_name,
            )
            .first()
        )
        if checklist:
            checklist.checklist_checked = True
            db.commit()
        db.close()

    def is_checklist_checked(self, immigrant_email: EmailStr, form_name: str) -> bool:
        db = self.Session()
        is_checked = False
        checklist = (
            db.query(ApplicationChecklists)
            .filter(
                ApplicationChecklists.immigrant_email == immigrant_email,
                ApplicationChecklists.form_name == form_name,
            )
            .first()
        )
        if checklist:
            is_checked = checklist.checklist_checked
        db.close()
        return is_checked

    def check_compiler_status(
        self, email: EmailStr, case_type: str, checklist: list, case_id: str = None
    ) -> dict[str, dict[str, Union[str, list[str], None]]]:
        db = self.Session()
        compiler_docs = (
            db.query(CompilerDocuments)
            .filter(
                CompilerDocuments.owner == email.lower(),
                CompilerDocuments.case_type == case_type,
            )
            .all()
        )
        if not compiler_docs:
            return {
                document: {
                    "file_url": None,
                    "file_size": None,
                    "status": "Missing",
                    "replace_reasons": None,
                }
                for document in checklist
            }
        compiler_docs = [doc for doc in compiler_docs]
        if case_id is not None:
            compiler_docs = [doc for doc in compiler_docs if doc.case_id == case_id]
        # print(f"Checklist: {checklist}")
        checklist_docs = {
            document: {
                "file_url": None,
                "file_size": None,
                "status": "Missing",
                "replace_reasons": None,
            }
            for document in checklist
        }
        # print(f"Checklist Docs: {checklist_docs}")
        for doc in compiler_docs:
            if doc.file_type in checklist_docs:
                checklist_docs[doc.file_type] = {
                    "file_url": doc.file_url,
                    "file_size": doc.file_size,
                    "status": "Present" if not doc.to_replace else "Replace",
                    "replace_reasons": doc.replace_reasons,
                }

        return checklist_docs

    def update_compiler_status(
        self, email: EmailStr, case_type: str, analysis_report: list, case_id: str
    ):
        db = self.Session()
        for documents in analysis_report:
            if documents["status"] != "Missing":
                to_replace = False
                if documents["status"] == "Replace":
                    to_replace = True
                temp_new_compiler = CompilerDocuments(
                    owner=email.lower(),
                    case_type=case_type,
                    file_name=os.path.basename(documents["file_url"]),
                    file_url=documents["file_url"],
                    file_type=documents["document_name"],
                    file_size=documents["file_size"],
                    case_id=case_id,
                    to_replace=to_replace,
                    replace_reasons=documents["replace_reasons"],
                )
                # print(temp_new_compiler)
                db.add(temp_new_compiler)
        db.commit()
        db.close()

    def replace_compiler_document(
        self,
        email: EmailStr,
        case_type: str,
        case_id: str,
        file_url: str,
        file_type: str,
        to_replace: bool = False,
        replace_reasons: str = None,
    ) -> None:
        db = self.Session()
        size = Helpers.get_url_file_size(file_url)
        compiler_docs = (
            db.query(CompilerDocuments)
            .filter(
                CompilerDocuments.owner == email.lower(),
                CompilerDocuments.case_type == case_type,
                CompilerDocuments.case_id == case_id,
                CompilerDocuments.file_type == file_type,
                CompilerDocuments.to_replace == True,
            )
            .all()
        )
        if compiler_docs:
            for compiler_doc in compiler_docs:
                compiler_doc.file_name = os.path.basename(compiler_doc.file_url)
                compiler_doc.file_url = file_url
                compiler_doc.to_replace = to_replace
                compiler_doc.replace_reasons = replace_reasons
                compiler_doc.file_size = size
            db.commit()
        db.close()

    def add_compiler_document(
        self,
        email: EmailStr,
        case_type: str,
        file_url: str,
        file_type: str,
        case_id: str,
        to_replace: bool = False,
        replace_reasons: str = None,
    ) -> None:
        db = self.Session()
        size = Helpers.get_url_file_size(file_url)
        new_compiler_doc = CompilerDocuments(
            owner=email.lower(),
            case_type=case_type,
            file_name=os.path.basename(file_url),
            file_url=file_url,
            file_type=file_type,
            file_size=size,
            case_id=case_id,
            to_replace=to_replace,
            replace_reasons=replace_reasons,
        )
        db.add(new_compiler_doc)
        db.commit()
        db.close()

    def get_case_matched_documents(
        self, email: EmailStr, case_type: str, case_id: str = None
    ) -> dict[str, str]:
        db = self.Session()
        compiler_docs = (
            db.query(CompilerDocuments)
            .filter(
                CompilerDocuments.owner == email.lower(),
                CompilerDocuments.case_type == case_type,
            )
            .all()
        )
        if case_id:
            compiler_docs = [doc for doc in compiler_docs if doc.case_id == case_id]
        documents_list = {}
        for doc in compiler_docs:
            documents_list[doc.file_type] = doc.file_url
        db.close()
        return documents_list

    def change_document_status(
        self,
        email: EmailStr,
        case_type: str,
        file_type: str,
        file_url: str,
        status: str,
        case_id: str = None,
    ) -> None:
        db = self.Session()
        compiler_docs = (
            db.query(CompilerDocuments)
            .filter(
                CompilerDocuments.owner == email.lower(),
                CompilerDocuments.case_type == case_type,
                CompilerDocuments.file_type == file_type,
                CompilerDocuments.file_url == file_url,
            )
            .all()
        )
        if compiler_docs:
            if case_id:
                compiler_docs = [doc for doc in compiler_docs if doc.case_id == case_id]
            for compiler_doc in compiler_docs:
                if status == "approved":
                    compiler_doc.to_replace = False
                    compiler_doc.replace_reasons = None
                    compiler_doc.verified = True
                elif status == "rejected":
                    compiler_doc.to_replace = True
                    compiler_doc.replace_reasons = "Incorrect matched file"
        #     print(f"Document {file_type} status changed to {status} for {email} in case type {case_type}")
        # else:
        #     print(f"Document {file_type} not found for {email} in case type {case_type}")
        db.commit()
        db.close()

    def retrieve_case_type(self, lawpersonnel_email: EmailStr, case_id: str) -> str:
        # TODO: Connect with Case Management Service
        pass

    def retrieve_client_cases(
        self, lawpersonnel_email: EmailStr, client_email: EmailStr
    ) -> list[dict[str, str]]:
        # TODO: Connect with Case Management Service
        pass

    def add_case_document(
        self,
        lawyer_email: EmailStr,
        case_id: str,
        document_url: str,
        filename: str,
        folder_name: str,
    ) -> tuple[str, str, str]:
        # TODO: Connect with Docs Service
        pass

    def retrieve_case_info(
        self, immigrant_username: str, case_type: str
    ) -> dict[str, Any]:
        # TODO: Connect with Case Management Service to get every detail
        pass

    def update_autofill_data(
        self,
        immigrant_username: str,
        form_name: str,
        field_descriptions: dict = None,
        immigrant_context: dict = None,
        immigrant_rag_context: str = None,
        autofill_data: dict = None,
    ) -> None:
        db = self.Session()
        existing_autofill_data = (
            db.query(AutofillData)
            .filter(
                AutofillData.immigrant_username == immigrant_username,
                AutofillData.form_name == form_name,
            )
            .first()
        )
        if not existing_autofill_data:
            new_autofill_data = AutofillData(
                immigrant_username=immigrant_username,
                form_name=form_name,
                form_data=autofill_data,
                field_descriptions=field_descriptions,
                immigrant_context=immigrant_context,
                immigrant_rag_context=immigrant_rag_context,
            )
            db.add(new_autofill_data)
            db.commit()
        else:
            existing_autofill_data.form_data = autofill_data
            if field_descriptions:
                existing_autofill_data.field_descriptions = field_descriptions
            if immigrant_context:
                existing_autofill_data.immigrant_context = immigrant_context
            if immigrant_rag_context:
                existing_autofill_data.immigrant_rag_context = immigrant_rag_context
            existing_autofill_data.created_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_autofill_data)

        db.close()

    def retrieve_autofill_data(
        self, immigrant_username: str, form_name: str
    ) -> AutofillData:
        db = self.Session()
        autofill_data = (
            db.query(AutofillData)
            .filter(
                AutofillData.immigrant_username == immigrant_username,
                AutofillData.form_name == form_name,
            )
            .first()
        )
        db.close()
        return autofill_data

    def create_fluency_profile(self, immigrant_email: EmailStr) -> FluencyProfile:
        db = self.Session()
        existing_profile = (
            db.query(FluencyProfile)
            .filter(FluencyProfile.immigrant_email == immigrant_email)
            .first()
        )
        if not existing_profile:
            new_profile = FluencyProfile(
                immigrant_email=immigrant_email, interaction_history=[]
            )
            db.add(new_profile)
            db.commit()
            db.refresh(new_profile)
            db.close()
            return new_profile
        db.close()
        return existing_profile

    def retrieve_fluency_profile(
        self, immigrant_email: EmailStr = None, profile_uuid: str = None
    ) -> FluencyProfile:
        db = self.Session()
        if immigrant_email:
            return self.create_fluency_profile(immigrant_email=immigrant_email)
        elif profile_uuid:
            existing_profile = (
                db.query(FluencyProfile)
                .filter(FluencyProfile.uuid == profile_uuid)
                .first()
            )
            db.close()
            return existing_profile

    def update_fluency_profile(
        self,
        immigrant_email: EmailStr,
        interaction_record: dict,
        strengths: list = [],
        areas_for_improvement: list = [],
        overall_fluency_score: float = 0.0,
    ):
        db = self.Session()
        profile = self.retrieve_fluency_profile(immigrant_email=immigrant_email)
        interaction_history = profile.interaction_history or []
        interaction_history.append(interaction_record)
        profile.interaction_history = interaction_history
        flag_modified(profile, "interaction_history")
        profile.strengths = strengths
        flag_modified(profile, "strengths")
        profile.areas_for_improvement = list(
            set(profile.areas_for_improvement + areas_for_improvement)
        )
        flag_modified(profile, "areas_for_improvement")
        profile.overall_fluency_score = overall_fluency_score
        flag_modified(profile, "overall_fluency_score")
        db.commit()
        db.refresh(profile)
        db.close()

    def retrieve_lawpersonnel_verification_items(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_type: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
    ) -> list[dict[str, Union[str, list[str]]]]:
        # TODO: connect with user management to get items
        pass

    def verify_lawpersonnel(self, lawpersonnel_email: EmailStr) -> None:
        # TODO: connect with usermanagement
        pass

    def delete_lawpersonnel_verification_items(
        self, lawpersonnel: LawPersonnel
    ) -> None:
        # TODO: connect with user management
        pass

    def delete_lawpersonnel_info(self, lawpersonnel: LawPersonnel) -> None:
        # TODO: connect with user management
        pass

    def delete_lawpersonnel(self, lawpersonnel_email: EmailStr) -> None:
        # TODO: connect with user management
        pass

    def retrieve_connected_lawyers(
        self, immigrant_email: EmailStr, case_id: str = None, only_emails: bool = False
    ) -> Union[
        EmailStr, list[EmailStr], list[dict[str, Union[EmailStr, str, bool, list[str]]]]
    ]:
        # TODO: connect with relationship management
        pass

    def retrieve_invitation_data(
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
        invited_email: EmailStr = None,
        invitee_email: EmailStr = None,
    ) -> Union[
        dict[EmailStr, str],
        list[dict[str, Union[str, EmailStr, list[EmailStr]]]],
        dict[EmailStr, dict[str, str]],
        EmailStr,
    ]:
        # TODO: connect with relationship management
        pass

    def retrieve_verified_lawyers(self) -> list[LawPersonnel]:
        # TODO: connect with user management
        pass

    def retrieve_external_lawyers(self) -> list[ExternalLawyer]:
        # TODO: connect with user management
        pass

    def update_lawyer_recommendations(
        self,
        client_email: EmailStr,
        registered_lawyers: list[EmailStr],
        unregistered_lawyers: list[EmailStr],
    ) -> None:
        db = self.Session()
        lawyer_recommendations = (
            db.query(LawyerRecommendations)
            .filter(LawyerRecommendations.client_email == client_email.lower())
            .first()
        )
        if not lawyer_recommendations:
            new_recommendations = LawyerRecommendations(
                client_email=client_email.lower(),
                registered_lawyers=[
                    reg_lawyer.lower() for reg_lawyer in registered_lawyers
                ],
                unregistered_lawyers=[
                    unreg_lawyer.lower() for unreg_lawyer in unregistered_lawyers
                ],
            )
            db.add(new_recommendations)
            db.commit()
        else:
            if (
                lawyer_recommendations.registered_lawyers
                != lawyer_recommendations.unregistered_lawyers
                != []
            ):
                lawyer_recommendations.registered_lawyers = registered_lawyers
                lawyer_recommendations.unregistered_lawyers = unregistered_lawyers
                db.commit()
                db.refresh(lawyer_recommendations)
        db.close()

    def get_lawyer_recommendations(
        self, client_email: EmailStr
    ) -> dict[str, list[EmailStr]]:
        db = self.Session()
        lawyer_recommendations = (
            db.query(LawyerRecommendations)
            .filter(LawyerRecommendations.client_email == client_email.lower())
            .first()
        )
        entries = {"registered": [], "unregistered": []}
        if lawyer_recommendations:
            entries["registered"] = lawyer_recommendations.registered_lawyers
            entries["unregistered"] = lawyer_recommendations.unregistered_lawyers

        return entries

    def remove_lawyer_from_recommendations(
        self, client_email: EmailStr, lawyer_email: EmailStr
    ) -> None:
        db = self.Session()
        lawyer_recommendations = (
            db.query(LawyerRecommendations)
            .filter(LawyerRecommendations.client_email == client_email.lower())
            .first()
        )
        if lawyer_recommendations:
            registered_lawyers = [
                lawyer
                for lawyer in lawyer_recommendations.registered_lawyers
                if lawyer != lawyer_email.lower()
            ]
            unregistered_lawyers = [
                lawyer
                for lawyer in lawyer_recommendations.unregistered_lawyers
                if lawyer != lawyer_email.lower()
            ]
            lawyer_recommendations.registered_lawyers = registered_lawyers
            lawyer_recommendations.unregistered_lawyers = unregistered_lawyers
            db.commit()
            db.refresh(lawyer_recommendations)
        db.close()

    def refresh_n400_quiz(self, email: EmailStr) -> None:
        db = self.Session()
        quiz_data = [
            {f"question_{i}": None, f"answer_{i}": None, f"submitted_answer_{i}": None}
            for i in range(1, 26)
        ]
        n400_quiz = (
            db.query(N400Quiz).filter(N400Quiz.immigrant_email == email.lower()).first()
        )
        if n400_quiz:
            n400_quiz.old_quiz_data.extend(n400_quiz.quiz_data)
            n400_quiz.quiz_data = quiz_data
            n400_quiz.start_date = datetime.now(timezone.utc)
            n400_quiz.end_date = None
            n400_quiz.quiz_completed = False
            n400_quiz.quiz_score = 0
            db.commit()
            db.refresh(n400_quiz)
        else:
            n400_quiz = N400Quiz(
                immigrant_email=email.lower(),
                quiz_data=quiz_data,
                start_date=datetime.now(timezone.utc),
            )
            db.add(n400_quiz)
            db.commit()
            db.refresh(n400_quiz)
        db.close()

    def add_n400_question(
        self, email: EmailStr, index_number: int, qa_pair: list[str]
    ) -> None:
        db = self.Session()
        n400_quiz = (
            db.query(N400Quiz).filter(N400Quiz.immigrant_email == email.lower()).first()
        )
        if n400_quiz:
            new_quiz = n400_quiz.quiz_data.copy() if n400_quiz.quiz_data else []
            if index_number <= len(new_quiz):
                new_quiz[index_number - 1] = {
                    **new_quiz[index_number - 1],
                    f"question_{index_number}": qa_pair[0],
                    f"answer_{index_number}": qa_pair[1],
                }

            n400_quiz.quiz_data = new_quiz
            db.commit()
            db.refresh(n400_quiz)
        db.close()

    def check_n400_answer(
        self, email: EmailStr, index_number: int, submitted_answer: str
    ) -> Union[bool, str]:
        db = self.Session()
        is_correct = False
        answer_string = None
        n400_quiz = (
            db.query(N400Quiz).filter(N400Quiz.immigrant_email == email.lower()).first()
        )
        if (
            n400_quiz
            and n400_quiz.quiz_data[index_number - 1][f"answer_{index_number}"]
            is not None
        ):
            answer = n400_quiz.quiz_data[index_number - 1].get(f"answer_{index_number}")
            new_quiz = n400_quiz.quiz_data.copy() if n400_quiz.quiz_data else []
            if index_number <= len(new_quiz):
                new_quiz[index_number - 1] = {
                    **new_quiz[index_number - 1],
                    f"submitted_answer_{index_number}": submitted_answer,
                }
            n400_quiz.quiz_data = new_quiz
            answer_string = answer
            if answer.lower() == submitted_answer.lower():
                n400_quiz.quiz_score += 1
                is_correct = True
            db.commit()
            db.refresh(n400_quiz)
        db.close()
        return is_correct, answer_string

    def retrieve_n400_score(self, email: EmailStr) -> tuple[str, list[dict[str, str]]]:
        db = self.Session()
        n400_quiz = (
            db.query(N400Quiz).filter(N400Quiz.immigrant_email == email.lower()).first()
        )
        score_string = "0 out of 25"
        quiz_data = []
        old_quiz_data = []
        if n400_quiz:
            n400_quiz.quiz_completed = True
            n400_quiz.end_date = datetime.now(timezone.utc)
            score_string = f"{n400_quiz.quiz_score} out of {len(n400_quiz.quiz_data)}"
            quiz_data = n400_quiz.quiz_data
            old_quiz_data = n400_quiz.old_quiz_data
            db.commit()
        db.close()
        return score_string, quiz_data, old_quiz_data

    def retrieve_n400_current(
        self, email: EmailStr
    ) -> list[dict[str, Union[str, list[str]]]]:
        db = self.Session()
        n400_quiz = (
            db.query(N400Quiz).filter(N400Quiz.immigrant_email == email.lower()).first()
        )
        if not n400_quiz or not n400_quiz.quiz_data:
            self.refresh_n400_quiz(email)
            n400_quiz = (
                db.query(N400Quiz)
                .filter(N400Quiz.immigrant_email == email.lower())
                .first()
            )

        return n400_quiz.quiz_data

    def calculate_active_cases(self, lawpersonnel_email: EmailStr) -> int:
        # TODO: Connect with case management to get active cases
        pass

    def get_case_details(
        self, lawpersonnel_email: EmailStr, case_id: str
    ) -> dict[str, Union[str, list[EmailStr]]]:
        # TODO: Connect with case management
        pass

    def get_task_details(self, task_id: str):
        # TODO: Connect with case management
        pass

    def get_case_members(
        self, lawpersonnel_email: EmailStr, case_id: str
    ) -> list[LawPersonnel]:
        member_emails = self.get_case_details(
            lawpersonnel_email=lawpersonnel_email, case_id=case_id
        ).get("assignee_list")
        return [
            self.get_lawpersonnel(member_email)
            for member_email in member_emails
            if self.get_lawpersonnel(member_email)
        ]

    def get_tasks(self, lawpersonnel_email: EmailStr, case_id: str):
        task_ids = self.get_case_details(
            lawpersonnel_email=lawpersonnel_email, case_id=case_id
        ).get("task_list")
        return [
            self.get_task_details(task_id)
            for task_id in task_ids
            if self.get_task_details(task_id)
        ]

    def get_lawyer_team(self, lawpersonnel_email: EmailStr) -> dict[str, str]:
        # TODO: Connect with case management
        pass

    def get_member_permissions(
        self, member_email: EmailStr, lawpersonnel_email: str
    ) -> str:
        if member_email == lawpersonnel_email:
            return "Admin"
        lawyer_team = self.get_lawyer_team(lawpersonnel_email=lawpersonnel_email)
        for member in lawyer_team:
            if member["member_email"] == member_email:
                return member["member_permissions"]
        return "Viewer"

    def update_twilio_context(
        self,
        user_number: str,
        user_context: str,
        ai_context: str,
        contact_method: Literal["call", "text", "whatsapp"],
    ) -> None:
        # db = self.Session()
        # today = datetime.now(timezone.utc)
        # start_date = today - timedelta(days=7)
        # twilio_context = (
        #     db.query(TwilioContext)
        #     .filter(
        #         TwilioContext.user_number == user_number,
        #         TwilioContext.contact_method == contact_method,
        #         TwilioContext.added_date >= start_date,
        #     )
        #     .order_by(TwilioContext.added_date.desc())
        #     .first()
        # )
        # if twilio_context:
        #     twilio_context.user_context = user_context
        #     twilio_context.ai_context = ai_context
        #     db.commit()
        #     db.refresh(twilio_context)
        # else:
        #     new_twilio_context = TwilioContext(
        #         user_number=user_number,
        #         user_context=user_context,
        #         ai_context=ai_context,
        #         contact_method=contact_method,
        #     )
        #     db.add(new_twilio_context)
        #     db.commit()
        # db.close()
        # TODO: Connect with communications database
        pass

    def add_twilio_interaction(
        self,
        user_number: str,
        contact_reason: str,
        contact_method: Literal["call", "text", "whatsapp"],
    ) -> None:
        # db = self.Session()
        # new_interaction = TwilioInteractions(
        #     user_number=user_number,
        #     contact_reason=contact_reason,
        #     contact_method=contact_method,
        # )
        # db.add(new_interaction)
        # db.commit()
        # add_record_to_airtable(new_interaction)
        # db.close()
        # TODO: Connect with communications database
        pass
