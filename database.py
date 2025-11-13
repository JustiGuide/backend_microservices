import os
from typing import Union, Literal
from pydantic import EmailStr
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    Float,
    String,
    Text,
    Boolean,
    create_engine,
)

from encryptor import EncryptedText, Encrypt
from datetime import datetime, timezone

load_dotenv()

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


class SubscriptionDetails(Base):
    __tablename__ = "subscription_details"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    user_email = Column(EncryptedText, nullable=False, index=True, unique=True)
    sub_tier = Column(Text, nullable=False)
    checkout_id = Column(EncryptedText, nullable=True)
    sub_id = Column(EncryptedText, nullable=True)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "user_email": self.user_email,
            "sub_tier": self.sub_tier,
            "checkout_id": self.checkout_id,
            "sub_id": self.sub_id,
        }

    def __repr__(self):
        return f"<SubscriptionDetails(uuid={self.uuid}, user_email={self.user_email}, sub_tier={self.sub_tier}, checkout_id={self.checkout_id}, sub_id={self.sub_id})>"


class ImmigrantNaturalization(Base):
    __tablename__ = "immigrant_naturalization"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    immigrant_email = Column(EncryptedText, nullable=False, index=True)
    checkout_id = Column(EncryptedText, nullable=True)
    is_paid = Column(Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "immigrant_email": self.immigrant_email,
            "checkout_id": self.checkout_id,
            "is_paid": self.is_paid,
        }

    def __repr__(self):
        return f"<ImmigrantNaturalization(uuid={self.uuid}, immigrant_email={self.immigrant_email}, checkout_id={self.checkout_id}, is_paid={self.is_paid})>"


class LawyerCaseSubs(Base):
    __tablename__ = "lawyer_case_subs"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    case_id = Column(EncryptedText, nullable=False, index=True)
    lawyer_email = Column(EncryptedText, nullable=False, index=True)
    case_type = Column(EncryptedText, nullable=False)
    client_email = Column(EncryptedText, nullable=False, index=True)
    case_checkout_id = Column(EncryptedText, nullable=True)
    case_sub_id = Column(EncryptedText, nullable=True)
    is_paid = Column(Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "case_id": self.case_id,
            "lawyer_email": self.lawyer_email,
            "case_type": self.case_type,
            "client_email": self.client_email,
            "case_checkout_id": self.case_checkout_id,
            "case_sub_id": self.case_sub_id,
            "is_paid": self.is_paid,
        }

    def __repr__(self):
        return f"<LawyerCaseSubs(uuid={self.uuid}, case_id={self.case_id}, lawyer_email={self.lawyer_email}, case_type={self.case_type}, client_email={self.client_email}, case_checkout_id={self.case_checkout_id}, case_sub_id={self.case_sub_id}, is_paid={self.is_paid})>"


class AllCases(Base):
    __tablename__ = "all_cases"
    case_id: str = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawyer_email: EmailStr = Column(EncryptedText, nullable=False, index=True)
    client_email: EmailStr = Column(EncryptedText, nullable=False, index=True)
    case_name: str = Column(EncryptedText, nullable=False)
    assignee_list: list[EmailStr] = Column(EncryptedText, nullable=True)
    task_list: list[str] = Column(EncryptedText, nullable=True)
    case_status: Literal["In Progress", "Submitted", "Closed"] = Column(EncryptedText, nullable=False, default="In Progress")
    case_description: str = Column(EncryptedText, nullable=True)
    form_submitted: bool = Column(Boolean, nullable=False, default=False)
    case_type: str = Column(EncryptedText, nullable=False)

    def to_dict(self):
        return {
            "case_id": self.case_id,
            "lawyer_email": self.lawyer_email,
            "client_email": self.client_email,
            "case_name": self.case_name,
            "assignee_list": self.assignee_list,
            "task_list": self.task_list,
            "case_status": self.case_status,
            "case_description": self.case_description,
            "form_submitted": self.form_submitted,
            "case_type": self.case_type,
        }

    def __repr__(self):
        return f"<AllCases(case_id={self.case_id}, lawyer_email={self.lawyer_email}, client_email={self.client_email}, case_name={self.case_name}, assignee_list={self.assignee_list}, task_list={self.task_list}, case_status={self.case_status}, case_description={self.case_description}, form_submitted={self.form_submitted}, case_type={self.case_type})>"


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

    def get_timestamp_from_id(self, message_timestamp: Union[str, int]) -> datetime:
        seconds = int(message_timestamp) / 1000
        return datetime.fromtimestamp(seconds, tz=timezone.utc)

    def get_current_timestamp(self) -> datetime:
        return datetime.now(timezone.utc)

    def retrieve_case_type(self, lawpersonnel_email: EmailStr, case_id: str) -> str:
        # TODO: Connect with Case Management Service
        pass

    def retrieve_connected_lawyers(
        self, immigrant_email: EmailStr, case_id: str = None, only_emails: bool = False
    ) -> Union[
        EmailStr, list[EmailStr], list[dict[str, Union[EmailStr, str, bool, list[str]]]]
    ]:
        # TODO: connect with relationship management
        pass

    def retrieve_verified_lawyers(self) -> list[LawPersonnel]:
        # TODO: connect with user management
        pass

    def update_checkout_id(
        self,
        user_email: EmailStr,
        checkout_id: str,
        sub_tier: Literal["plus", "nonlawyer", "lawyer", "clinic", "enterprise"],
    ) -> None:
        db = self.Session()
        user_subscription = (
            db.query(SubscriptionDetails)
            .filter(SubscriptionDetails.user_email == user_email.lower())
            .first()
        )
        if user_subscription:
            user_subscription.sub_tier = sub_tier
            user_subscription.checkout_id = checkout_id
            db.commit()
            db.refresh(user_subscription)
        else:
            new_user_subscription = SubscriptionDetails(
                user_email=user_email.lower(),
                sub_tier=sub_tier,
                checkout_id=checkout_id,
            )
            db.add(new_user_subscription)
            db.commit()
        db.close()

    def retrieve_naturalization_checkout_id(self, user_email: EmailStr) -> str:
        db = self.Session()
        naturalization_sub = (
            db.query(ImmigrantNaturalization)
            .filter(ImmigrantNaturalization.immigrant_email == user_email.lower())
            .first()
        )
        checkout_id = None
        if naturalization_sub:
            checkout_id = naturalization_sub.checkout_id
        db.close()
        return checkout_id

    def update_naturalization_checkout_id(
        self, user_email: EmailStr, checkout_id: str
    ) -> None:
        db = self.Session()
        naturalization_sub = (
            db.query(ImmigrantNaturalization)
            .filter(ImmigrantNaturalization.immigrant_email == user_email.lower())
            .first()
        )
        if naturalization_sub:
            naturalization_sub.checkout_id = checkout_id
            db.commit()
            db.refresh(naturalization_sub)
        else:
            new_naturalization_sub = ImmigrantNaturalization(
                immigrant_email=user_email.lower(),
                checkout_id=checkout_id,
            )
            db.add(new_naturalization_sub)
            db.commit()
        db.close()

    def check_naturalization(self, user_email: EmailStr) -> None:
        db = self.Session()
        naturalization_sub = (
            db.query(ImmigrantNaturalization)
            .filter(ImmigrantNaturalization.immigrant_email == user_email.lower())
            .first()
        )
        if naturalization_sub and naturalization_sub.is_paid:
            return True
        return False

    def paid_naturalization(self, user_email: EmailStr, checkout_id: str) -> None:
        db = self.Session()
        naturalization_sub = (
            db.query(ImmigrantNaturalization)
            .filter(
                ImmigrantNaturalization.immigrant_email == user_email.lower(),
                ImmigrantNaturalization.checkout_id == checkout_id,
            )
            .first()
        )
        if naturalization_sub:
            naturalization_sub.is_paid = True
            db.commit()
            db.refresh(naturalization_sub)
        else:
            new_naturalization_sub = ImmigrantNaturalization(
                immigrant_email=user_email.lower(),
                checkout_id=checkout_id,
                is_paid=True,
            )
            db.add(new_naturalization_sub)
            db.commit()
        db.close()

    def remove_naturalization_entry(self, user_email: EmailStr) -> None:
        db = self.Session()
        naturalization_subs = (
            db.query(ImmigrantNaturalization)
            .filter(ImmigrantNaturalization.immigrant_email == user_email.lower())
            .all()
        )
        if naturalization_subs:
            for naturalization_sub in naturalization_subs:
                if naturalization_sub:
                    db.delete(naturalization_sub)
                    db.commit()
        db.close()

    def update_subscription_id(self, user_email: EmailStr, sub_id: str) -> None:
        db = self.Session()
        user_subscription = (
            db.query(SubscriptionDetails)
            .filter(SubscriptionDetails.user_email == user_email.lower())
            .first()
        )
        if user_subscription:
            user_subscription.sub_id = sub_id
            db.commit()
            db.refresh(user_subscription)
        db.close()

    def update_subscription_details(
        self,
        user_email: EmailStr,
        sub_tier: Literal["plus", "nonlawyer", "lawyer", "clinic", "enterprise", "free"],
        checkout_id: str,
        sub_id: str,
    ) -> None:
        db = self.Session()
        user_subscription = (
            db.query(SubscriptionDetails)
            .filter(SubscriptionDetails.user_email == user_email.lower())
            .first()
        )
        if user_subscription:
            user_subscription.sub_tier = sub_tier
            user_subscription.checkout_id = checkout_id
            user_subscription.sub_id = sub_id
            db.commit()
            db.refresh(user_subscription)
        else:
            new_user_subscription = SubscriptionDetails(
                user_email=user_email.lower(),
                sub_tier=sub_tier,
                checkout_id=checkout_id,
                sub_id=sub_id,
            )
            db.add(new_user_subscription)
            db.commit()
        db.close()

    def retrieve_subscription_details(
        self, user_email: EmailStr
    ) -> tuple[str, str, str]:
        db = self.Session()
        user_subscription = (
            db.query(SubscriptionDetails)
            .filter(SubscriptionDetails.user_email == user_email.lower())
            .first()
        )
        sub_tier = None
        checkout_id = None
        sub_id = None
        if user_subscription:
            sub_tier = user_subscription.sub_tier
            checkout_id = user_subscription.checkout_id
            sub_id = user_subscription.sub_id

        db.close()
        return sub_tier, checkout_id, sub_id

    def update_lawyer_case_sub(
        self,
        case_id: str,
        lawyer_email: EmailStr,
        case_sub_id: str = None,
        case_type: Literal[
            "nonimmigrant_worker",
            "employment_auth",
            "alien_rel",
            "asylum_removal",
            "naturalization",
        ] = None,
        client_email: EmailStr = None,
        case_checkout_id: str = None,
    ) -> None:
        db = self.Session()
        case_sub = (
            db.query(LawyerCaseSubs)
            .filter(
                LawyerCaseSubs.lawyer_email == lawyer_email.lower(),
                LawyerCaseSubs.case_id == case_id,
            )
            .first()
        )
        is_paid = False
        if case_sub_id:
            is_paid = True
        if case_sub:
            if case_sub_id:
                case_sub.case_sub_id = case_sub_id
                case_sub.is_paid = is_paid
            if case_checkout_id:
                case_sub.case_checkout_id = case_checkout_id
            db.commit()
            db.refresh(case_sub)
        else:
            new_case_sub = LawyerCaseSubs(
                lawyer_email=lawyer_email.lower(),
                case_type=case_type,
                case_id=case_id,
                client_email=client_email.lower(),
                case_checkout_id=case_checkout_id,
                case_sub_id=case_sub_id,
                is_paid=is_paid,
            )
            db.add(new_case_sub)
            db.commit()

        db.close()

    def retrieve_case_from_checkout(
        self, checkout_id: str
    ) -> dict[str, Union[EmailStr, str, bool]]:
        db = self.Session()
        case_sub = (
            db.query(LawyerCaseSubs.case_id)
            .filter(LawyerCaseSubs.case_checkout_id == checkout_id)
            .first()
        )
        case_id = None
        if case_sub:
            case_id = case_sub[0]
        db.close()
        return case_id

    def retrieve_lawyer_case_sub(
        self, case_id: str
    ) -> dict[str, Union[EmailStr, str, bool]]:
        db = self.Session()
        case_sub = (
            db.query(LawyerCaseSubs).filter(LawyerCaseSubs.case_id == case_id).first()
        )
        if case_sub:
            db.close()
            return case_sub.to_dict()
        db.close()
        return {}

    def delete_lawyer_case_sub(self, case_id: str) -> None:
        db = self.Session()
        case_sub = (
            db.query(LawyerCaseSubs).filter(LawyerCaseSubs.case_id == case_id).first()
        )
        if case_sub:
            case_sub.case_checkout_id = None
            case_sub.case_sub_id = None
            case_sub.is_paid = False
            db.commit()
        db.close()

    def retrieve_lawpersonnel_case_subs(self, case_ids: list[str]):
        db = self.Session()
        case_subs = db.query(LawyerCaseSubs.case_id, LawyerCaseSubs.is_paid).filter(LawyerCaseSubs.case_id.in_(case_ids)).all()
        return {sub[0]: sub[1] for sub in case_subs}

    def check_case(self, case_id: str) -> tuple[str, EmailStr, EmailStr]:
        # TODO: connect with case management
        pass

    def update_user_subscription(
        self,
        user_type: Literal["immigrant", "lawpersonnel"],
        subscriber_email: EmailStr,
        subscription_type: Literal["free", "pay", "plus", "enterprise"],
    ) -> None:
        # TODO: Connect with user management
        # db = self.Session()
        # user = db.query(User).filter(User.email == email).first()
        # if user:
        #     if subscription_type != "free":
        #         if subscription_type == "pay":
        #             user.user_limit += 10
        #         else:
        #             user.user_limit = math.inf
        #     elif user.subscription_type not in ["free", "pay"]:
        #         user.user_limit = 10

        #     user.subscription_type = subscription_type
        #     db.commit()
        #     db.refresh(user)
        #     refresh_airtable_record(user)
        # db.close()
        pass

    def start_case(self, lawyer_email: EmailStr, case_id: str) -> bool:
        # TODO: connect with case management, update current 1st task as Done, call task generator to retrieve and add new tasks
        pass
