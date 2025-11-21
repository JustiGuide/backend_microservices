import math
import os
from random import randint
import re
from typing import Any, Union, Literal
from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy.orm import sessionmaker, declarative_base, validates
from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    LargeBinary,
    String,
    Text,
    Boolean,
    create_engine,
    func,
)
from encryptor import EncryptedText, Encrypt
from datetime import date, datetime, timedelta, timezone

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


class CrawlPost(Base):
    __tablename__ = "crawl_posts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    content = Column(Text)
    link = Column(String, nullable=True)
    release_date = Column(String, nullable=True)
    last_updated = Column(String, nullable=True)
    prompted_assistant = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "link": self.link,
            "release_date": self.release_date,
            "last_updated": self.last_updated,
            "prompted_assistant": self.prompted_assistant,
            "timestamp": self.timestamp,
        }

    def __repr__(self):
        return f"<CrawlPost(id={self.id}, title={self.title}, link={self.link}, prompted_assistant={self.prompted_assistant})>"


class LobRecord(Base):
    __tablename__ = "lob_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    form_name = Column(String, default="N400")
    lob_type = Column(String, nullable=False)
    lob_id = Column(String, nullable=False)
    lob_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<LobRecord(username='{self.username}', lob_type='{self.lob_type}', lob_id='{self.lob_id}')>"


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

    def update_user_receipt_number(
        self, email_id: EmailStr, receipt_number: str
    ) -> None:
        # db = self.Session()
        # user = db.query(Immigrants).filter(Immigrants.email == email_id.lower()).first()
        # if user:
        #     user.receipt_number = receipt_number
        #     db.commit()
        # db.close()
        # TODO: connect with users module
        pass

    def save_crawler_data(self, posts):
        db = self.Session()
        saved_posts = db.query(CrawlPost.link).all()
        try:
            for post in posts:
                if not post["link"] in saved_posts:
                    new_crawl_post = CrawlPost(
                        title=post["title"],
                        content=post["content"],
                        link=post["link"],
                        release_date=datetime.strptime(
                            post["release_date"], "%m/%d/%Y"
                        ).strftime("%Y-%m-%d"),
                        last_updated=datetime.strptime(
                            post["last_updated"], "%m/%d/%Y"
                        ).strftime("%Y-%m-%d"),
                    )
                    db.add(new_crawl_post)
                    db.commit()
                print(f">>>Post From: {post['link']}, Exists.")
            db.close()
            return {"message": f"Crawl Completed and Posts Saved Accordingly."}
        except Exception as error:
            db.close()
            return {"error": f"An Error Occurred: {error}"}

    def retrieve_crawler_data(self):
        db = self.Session()
        crawled_data = db.query(CrawlPost).all()
        db.close()
        return crawled_data

    def get_prompted_crawled_data(self):
        db = self.Session()
        prompted_crawled_data = (
            db.query(CrawlPost).filter(CrawlPost.prompted_assistant == True).all()
        )
        db.close()
        return prompted_crawled_data

    def get_unprompted_crawled_data(self):
        db = self.Session()
        unprompted_crawled_data = (
            db.query(CrawlPost).filter(CrawlPost.prompted_assistant == False).all()
        )
        db.close()
        return unprompted_crawled_data

    def update_prompted_status(self, data_id, prompted):
        db = self.Session()
        post = db.query(CrawlPost).filter(CrawlPost.id == data_id).first()
        if post:
            post.prompted_assistant = prompted

            db.commit()
            db.refresh(post)
        db.close()
        return post

    def save_lob_record(
        self, username, lob_id, lob_type, form_name="N400", metadata=None
    ):
        db = self.Session()
        try:
            record = LobRecord(
                username=username,
                lob_id=lob_id,
                lob_type=lob_type,
                form_name=form_name,
                metadata=metadata,
            )
            db.add(record)
            db.commit()
            db.close()
            return record
        except Exception as e:
            db.rollback()
            db.close()
            print(f"Error saving Lob record: {str(e)}")
            return None

    def delete_lob_record_by_id(self, lob_id: str, lob_type: str = "address"):
        db = self.Session()
        try:
            record = (
                db.query(LobRecord).filter_by(lob_id=lob_id, lob_type=lob_type).first()
            )
            if record:
                db.delete(record)
                db.commit()
                db.close()
                return True
            db.close()
            return False
        except Exception as e:
            db.rollback()
            db.close()
            raise e

    def retrieve_form_details(self, form_name: str, immigrant_email: EmailStr) -> dict:
        # db = self.Session()
        # form = (
        #     db.query(FormDetails)
        #     .filter(
        #         FormDetails.immigrant_email == immigrant_email,
        #         FormDetails.form_name == form_name,
        #     )
        #     .first()
        # )
        # if not form:
        #     db.close()
        #     return "Form not found"
        # form_details = form.form_details
        # db.close()
        # return form_details
        # TODO: connect with docs service
        pass
