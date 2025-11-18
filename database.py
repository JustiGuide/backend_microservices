import json
import os
from typing import Literal, Union
from pydantic import EmailStr
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from sqlalchemy import Column, Float, String, Text, Boolean, create_engine
from encryptor import EncryptedText
from datetime import datetime

load_dotenv()

Base = declarative_base()


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

    def retrieve_all_lawpersonnel_files(
        self, lawpersonnel_username: str, lawpersonnel_type: Literal["lawyers", "nonlawyers", "paralegals", "lawstudents"]
    ) -> dict[str, list[str]]:
        lawpersonnel_files: dict[str, list[str]] = {}
        file_subfolders = ["ai_chat_files", "personal_files", "profile_picture", "government_ids"]
        if lawpersonnel_type == "lawyers":
            file_subfolders.extend(
                ["intakes", "professional_licenses", "address_proofs"]
            )
        for subfolder in file_subfolders:
            lawpersonnel_files[subfolder] = []
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"{lawpersonnel_type}/{lawpersonnel_username.lower()}/{subfolder}/",
            )
            if "Contents" in response:
                for obj in response["Contents"]:
                    file_key: str = obj["Key"]
                    filename = file_key.split("/")[-1]
                    if (
                        filename
                        and "blob" not in filename
                        and not self._is_image(filename)
                    ):
                        lawpersonnel_files[subfolder].append(
                            f"{self.base_url}/{file_key}"
                        )
        return lawpersonnel_files

    def get_immigrant_kyc(self, parameter: Union[EmailStr, str]) -> dict:
        # TODO: connect with user management
        pass

    def process_immigrant_messages(
        self, immigrant_email: EmailStr
    ) -> dict[
        str, dict[str, dict[str, Union[str, list[str], dict[str, list[str]], datetime]]]
    ]:
        # db = self.Session()
        # messages = (
        #     db.query(ImmigrantAIChat)
        #     .filter(ImmigrantAIChat.immigrant_email == immigrant_email.lower())
        #     .all()
        # )
        # result = {}
        # if messages:
        #     for message in messages:
        #         if message.sender not in result:
        #             result[message.sender] = {}

        #         new_urls = []
        #         doc_sizes = []
        #         for document in message.document_urls:
        #             file = self.retrieve_file(document)
        #             if file:
        #                 new_urls.append(
        #                     f"{os.getenv('BACKEND')}file/{file.uuid}/{file.file_name}"
        #                 )
        #                 doc_sizes.append(file.file_size)

        #         result[message.sender][message.uuid] = {
        #             "message": message.message,
        #             "references": message.references,
        #             "timestamp": message.timestamp,
        #             "feedback": message.feedback,
        #             "vote": message.vote,
        #             "documents": new_urls,
        #             "document_sizes": doc_sizes,
        #         }
        # db.close()
        # return result
        # TODO: connect with ai agent module
        pass

    def process_lawpersonnel_messages(
        self, lawpersonnel_email: EmailStr, starred: bool = False
    ) -> dict[
        str, dict[str, dict[str, Union[str, list[str], dict[str, list[str]], datetime]]]
    ]:
        # db = self.Session()
        # messages = (
        #     db.query(LawPersonnelAIChat)
        #     .filter(LawPersonnelAIChat.lawpersonnel_email == lawpersonnel_email.lower())
        #     .all()
        # )
        # result = {}
        # if messages:
        #     for message in messages:
        #         if message.sender not in result:
        #             result[message.sender] = {}

        #         new_urls = []
        #         doc_sizes = []
        #         for document in message.document_urls:
        #             file = self.retrieve_file(document)
        #             if file:
        #                 new_urls.append(
        #                     f"{os.getenv('BACKEND')}file/{file.uuid}/{file.file_name}"
        #                 )
        #                 doc_sizes.append(file.file_size)

        #         message_dictionary = {
        #             "message": message.message,
        #             "references": message.references,
        #             "timestamp": message.timestamp,
        #             "feedback": message.feedback,
        #             "vote": message.vote,
        #             "documents": new_urls,
        #             "document_sizes": doc_sizes,
        #         }

        #         if not starred or message.favorite_bool:
        #             result[message.sender][message.uuid] = message_dictionary
        # db.close()
        # return result
        # TODO: connect with ai agent module
        pass

    def retrieve_user_messages(self, user_email: EmailStr, user_type: Literal["immigrant", "lawyer", "nonlawyer", "lawstudent", "paralegal"]):
        message_history = self.process_immigrant_messages(immigrant_email=user_email)
        if user_type != "immigrant":
            message_history = self.process_lawpersonnel_messages(lawpersonnel_email=user_email)

        messages = [message_history["user"][uuid]["message"] for uuid in message_history["user"] if len(message_history.keys()) > 0 and "user" in message_history]
        return messages

    def load_kyc_map(self) -> dict[str, list[str]]:
        kyc_desc = {}
        with open("./data/kyc_mapping.json", "r") as exp:
            kyc_desc = json.load(exp)

        return kyc_desc
