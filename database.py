import os
from typing import Any, Union, Literal
from fastapi import HTTPException
from pydantic import EmailStr, HttpUrl
from sqlalchemy.orm import sessionmaker, declarative_base, validates
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    LargeBinary,
    String,
    Text,
    Boolean,
    create_engine,
    func,
    or_,
)
from encryptor import EncryptedText, Encrypt
from datetime import date, datetime, timezone

load_dotenv()


Base = declarative_base()


class ScheduledFunctions(Base):
    __tablename__ = "scheduled_functions"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    func_name = Column(LargeBinary, nullable=False)
    args = Column(EncryptedText, nullable=False)
    kwargs = Column(EncryptedText, nullable=False)
    scheduled_date = Column(DateTime(timezone=True), nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "func_name": self.func_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "scheduled_date": self.scheduled_date,
        }

    def __repr__(self):
        return f"<ScheduledFunctions(uuid={self.uuid}, func_name={self.func_name}, args={self.args}, kwargs={self.kwargs}, scheduled_date={self.scheduled_date})>"


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


class ImmigrantLawyerConnection(Base):
    __tablename__ = "immigrant_lawyer_connection"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    immigrant_email = Column(EncryptedText, nullable=False, index=True)
    lawyer_email = Column(EncryptedText, nullable=False, index=True)
    lawyer_case_ids = Column(EncryptedText, nullable=True, default=[])
    connected_boolean = Column(Boolean, nullable=False, default=False)
    saved_boolean = Column(Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "immigrant_email": self.immigrant_email,
            "lawyer_email": self.lawyer_email,
            "lawyer_case_ids": self.lawyer_case_ids,
            "connected_boolean": self.connected_boolean,
            "saved_boolean": self.saved_boolean
        }
    
    def __repr__(self):
        return f"<ImmigrantLawyerConnection(uuid={self.uuid}, immigrant_email={self.immigrant_email}, lawyer_email={self.lawyer_email}, lawyer_case_ids={self.lawyer_case_ids}, connected_boolean={self.connected_boolean}, saved_boolean={self.saved_boolean})>"

class Invitations(Base):
    __tablename__ = "invitations"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    invited_type = Column(String(50), nullable=False)
    invitee_email = Column(EncryptedText, nullable=False, index=True)
    invited_email = Column(EncryptedText, nullable=False)
    case_type = Column(EncryptedText, nullable=True)
    client_number = Column(EncryptedText, nullable=True)
    client_address = Column(EncryptedText, nullable=True)
    case_id = Column(String(7), nullable=True)
    member_role = Column(String(50), nullable=True)
    member_permissions = Column(EncryptedText, nullable=True)
    case_name = Column(EncryptedText, nullable=True)
    case_description = Column(EncryptedText, nullable=True)
    assignees = Column(EncryptedText, nullable=True)
    
    def to_dict(self):
        return {
            "uuid": self.uuid,
            "invited_type": self.invited_type,
            "invitee_email": self.invitee_email,
            "invited_email": self.invited_email,
            "case_type": self.case_type,
            "client_number": self.client_number,
            "client_address": self.client_address,
            "case_id": self.case_id,
            "member_role": self.member_role,
            "member_permissions": self.member_permissions,
            "case_name": self.case_name,
            "case_description": self.case_description,
            "assignees": self.assignees,
        }
    
    def __repr__(self):
        return f"<Invitations(uuid={self.uuid}, invited_type={self.invited_type}, invitee_email={self.invitee_email}, invited_email={self.invited_email}, case_type={self.case_type}, client_number={self.client_number}, client_address={self.client_address}, case_id={self.case_id}, member_role={self.member_role}, member_permissions={self.member_permissions}, case_name={self.case_name}, case_description={self.case_description}, assignees={self.assignees})>"

class AllClients(Base):
    __tablename__ = "all_clients"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawyer_email = Column(EncryptedText, nullable=False, index=True)
    client_email = Column(EncryptedText, nullable=False)
    client_number = Column(EncryptedText, nullable=False)
    client_address = Column(EncryptedText, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "lawyer_email": self.lawyer_email,
            "client_email": self.client_email,
            "client_number": self.client_number,
            "client_address": self.client_address
        }

    def __repr__(self):
        return f"<AllClients(uuid={self.uuid}, lawyer_email={self.lawyer_email}, client_email={self.client_email}, client_number={self.client_number}, client_address={self.client_address})>"


class AllCases(Base):
    __tablename__ = "all_cases"
    case_id = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawyer_email = Column(EncryptedText, nullable=False, index=True)
    client_email = Column(EncryptedText, nullable=False, index=True)
    case_name = Column(EncryptedText, nullable=False)
    assignee_list = Column(EncryptedText, nullable=True)
    task_list = Column(EncryptedText, nullable=True)
    case_status = Column(EncryptedText, nullable=False, default="In Progress")
    case_description = Column(EncryptedText, nullable=True)
    form_submitted = Column(Boolean, nullable=False, default=False)
    case_type = Column(EncryptedText, nullable=False)

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


class ClientIntake(Base):
    __tablename__ = "client_intake"
    uuid = Column(String(7), primary_key=True, nullable=False, default=Encrypt.generate_uuid)
    lawyer_email = Column(EncryptedText, nullable=False)
    client_email = Column(EncryptedText, nullable=False)
    case_id = Column(EncryptedText, nullable=False)
    case_type = Column(EncryptedText)
    intake_form_id = Column(String(7), nullable=False)
    date_sent = Column(Date)
    date_signed = Column(Date)
    handshake_id = Column(String(7), nullable=False, default=False)
    intake_form_url = Column(EncryptedText, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "lawyer_email": self.lawyer_email,
            "client_email": self.client_email,
            "case_id": self.case_id,
            "case_type": self.case_type,
            "intake_form_id": self.intake_form_id,
            "date_sent": self.date_sent,
            "date_signed": self.date_signed,
            "handshake_id": self.handshake_id,
            "intake_form_url": self.intake_form_url
        }
    
    def __repr__(self):
        return f"<ClientIntake(uuid={self.uuid}, lawyer_email={self.lawyer_email}, client_email={self.client_email}, case_id={self.case_id}, case_type={self.case_type}, intake_form_id={self.intake_form_id}, date_sent={self.date_sent}, date_signed={self.date_signed}, handshake_id={self.handshake_id}, intake_form_url={self.intake_form_url})>"

class LawyerForms(Base):
    __tablename__ = "lawyer_intake_forms"
    uuid = Column(String(7), primary_key=True, nullable=False, default=Encrypt.generate_uuid)
    lawyer_email = Column(EncryptedText, nullable=False)
    form_name = Column(EncryptedText, nullable=False)
    form_url = Column(EncryptedText, nullable=False)
    form_md5 = Column(EncryptedText, nullable=False)
    upload_date = Column(Date, nullable=False)
    last_used_case_type = Column(EncryptedText)
    last_used = Column(Date)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "lawyer_email": self.lawyer_email,
            "form_name": self.form_name,
            "form_url": self.form_url,
            "form_md5": self.form_md5,
            "upload_date": self.upload_date,
            "last_used_case_type": self.last_used_case_type,
            "last_used": self.last_used
        }
    
    def __repr__(self):
        return f"<LawyerForms(uuid={self.uuid}, lawyer_email={self.lawyer_email}, form_name={self.form_name}, form_url={self.form_url}, form_md5={self.form_md5}, upload_date={self.upload_date}, last_used_case_type={self.last_used_case_type}, last_used={self.last_used})>"


class Connection:
    def __init__(self, database_actor="postgresql"):
        self.connection_string = f"""{database_actor}://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}"""
        self.engine = create_engine(self.connection_string)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )


class ConnectionRequests(Base):
    __tablename__ = "connection_requests"
    id = Column(String(7), primary_key=True, index=True, default=Encrypt.generate_uuid)
    message = Column(EncryptedText, nullable=False)
    sender_email = Column(EncryptedText, nullable=True)
    recipient_email = Column(EncryptedText, nullable=True)
    status = Column(String, default="Pending")
    status_changed = Column(DateTime, nullable=True)
    timestamp = Column(DateTime, default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "sender_email": self.sender_email,
            "recipient_email": self.recipient_email,
            "status": self.status,
        }

    def __repr__(self):
        return f"<SentMessage(id={self.id}, sender_email={self.sender_email}, recipient_email={self.recipient_email}, status={self.status})>"

    @validates("status")
    def validate_status(self, key, value):
        if value:
            self.status_changed = func.now()
        return value


class Functions:
    db = Connection()
    Session = db.SessionLocal

    def add_scheduled_function(
        self,
        func_name: str,
        scheduled_date: datetime,
        args: tuple,
        kwargs: dict[str, Any],
    ) -> str:
        db = self.Session()
        unique_id = None
        scheduled_function = (
            db.query(ScheduledFunctions)
            .filter(
                ScheduledFunctions.func_name == func_name,
                ScheduledFunctions.args == args,
                ScheduledFunctions.kwargs == kwargs,
                ScheduledFunctions.scheduled_date == scheduled_date,
            )
            .first()
        )
        if not scheduled_function:
            scheduled_function = ScheduledFunctions(
                func_name=func_name,
                scheduled_date=scheduled_date,
                args=args,
                kwargs=kwargs,
            )
            db.add(scheduled_function)
            db.commit()

        unique_id = scheduled_function.uuid
        db.close()
        return unique_id

    def retrieve_scheduled_functions(
        self,
    ) -> dict[str, dict[str, Union[str, datetime, tuple, dict[str, Any]]]]:
        db = self.Session()
        scheduled_functions = {}
        all_functions = db.query(ScheduledFunctions).all()
        for function in all_functions:
            scheduled_functions[function.uuid] = {
                "function": function.func_name,
                "run_date": function.scheduled_date,
                "args": function.args,
                "kwargs": function.kwargs,
            }
        db.close()
        return scheduled_functions

    def delete_scheduled_function(self, function_id: str) -> None:
        db = self.Session()
        scheduled_function = (
            db.query(ScheduledFunctions)
            .filter(ScheduledFunctions.uuid == function_id)
            .first()
        )
        if scheduled_function:
            db.delete(scheduled_function)
            db.commit()

        db.close()

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

    def update_lawyer_stat(self, lawyer_email: EmailStr, stat_type: str) -> None:
        # db = self.Session()
        # today = date.today()
        # lawyer_stat = (
        #     db.query(LawyerStats)
        #     .filter(
        #         LawyerStats.lawyer_email == lawyer_email.lower(),
        #         LawyerStats.stat_type == stat_type,
        #         LawyerStats.stat_date == today,
        #     )
        #     .first()
        # )
        # if lawyer_stat:
        #     lawyer_stat.stat_val = lawyer_stat.stat_val + 1
        # else:
        #     lawyer_stat = LawyerStats(
        #         lawyer_email=lawyer_email.lower(),
        #         stat_date=today,
        #         stat_type=stat_type,
        #     )
        #     db.add(lawyer_stat)
        # db.commit()
        # db.close()
        # TODO: Connect with user management
        pass

    def get_all_casetypes(
        self,
    ) -> dict[str, dict[str, Union[str, list[dict[str, Union[str, int]]]]]]:
        # TODO: Connect with case management service to get all case type (case_type.json)
        return {}

    def get_all_formnames(self) -> list[str]:
        all_casetypes = self.get_all_casetypes()
        return [case["form"] for case in all_casetypes.values()]

    def get_all_casename_slugs(self) -> list[str]:
        all_casetypes = self.get_all_casetypes()
        return [case for case in all_casetypes.keys()]

    def get_casename(self, case_type: str) -> str:
        all_casetypes = self.get_all_casetypes()
        return all_casetypes[case_type]['case']

    def update_clients(
        self,
        lawpersonnel_email: EmailStr,
        client_email: EmailStr,
        client_number: str,
        client_address: str,
    ) -> None:
        db = self.Session()
        exist_client = (
            db.query(AllClients)
            .filter(
                AllClients.lawyer_email == lawpersonnel_email.lower(),
                AllClients.client_email == client_email.lower(),
            )
            .first()
        )
        if not exist_client:
            self.update_lawyer_stat(lawpersonnel_email, "client_num")
            new_client = AllClients(
                lawyer_email=lawpersonnel_email.lower(),
                client_email=client_email.lower(),
                client_number=client_number,
                client_address=client_address,
            )
            db.add(new_client)
            db.commit()
        else:
            exist_client.client_number = client_number
            exist_client.client_address = client_address
            db.commit()
            db.refresh(exist_client)

        db.close()

    def retrieve_all_clients(self, lawpersonnel_email: EmailStr) -> list[EmailStr]:
        db = self.Session()
        all_clients = []
        clients = (
            db.query(AllClients)
            .filter(AllClients.lawyer_email == lawpersonnel_email.lower())
            .all()
        )
        for client in clients:
            all_clients.append(client.client_email)

        db.close()
        return all_clients

    def retrieve_client_details(
        self, lawpersonnel_email: EmailStr, immigrant_email: EmailStr
    ) -> dict[str, str]:
        db = self.Session()
        details = {}
        client = (
            db.query(AllClients)
            .filter(
                AllClients.lawyer_email == lawpersonnel_email.lower(),
                AllClients.client_email == immigrant_email.lower(),
            )
            .first()
        )
        if client:
            details["client_number"] = client.client_number
            details["client_address"] = client.client_address

        db.close()
        return details

    def check_client(
        self, immigrant_email: EmailStr, lawpersonnel_email: EmailStr
    ) -> bool:
        db = self.Session()
        client = (
            db.query(AllClients)
            .filter(
                AllClients.lawyer_email == lawpersonnel_email.lower(),
                AllClients.client_email == immigrant_email.lower(),
            )
            .first()
        )
        if client:
            db.close()
            return True
        db.close()
        return False

    def update_connected_lawyers(
        self, immigrant_email: EmailStr, lawyer_email: EmailStr, case_id: str
    ) -> None:
        db = self.Session()
        connected_lawyer = (
            db.query(ImmigrantLawyerConnection)
            .filter(
                ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
                ImmigrantLawyerConnection.lawyer_email == lawyer_email.lower(),
                ImmigrantLawyerConnection.connected_boolean == True,
            )
            .first()
        )
        if connected_lawyer:
            if case_id not in connected_lawyer.lawyer_case_ids and case_id is not None:
                connected_lawyer.lawyer_case_ids.append(case_id)
        else:
            connected_lawyer = ImmigrantLawyerConnection(
                immigrant_email=immigrant_email.lower(),
                lawyer_email=lawyer_email.lower(),
                lawyer_case_ids=[case_id],
                connected_boolean=True,
            )
            db.add(connected_lawyer)
        db.commit()
        db.close()

    def retrieve_conn_lawyer_emails(self, immigrant_email: EmailStr) -> list[EmailStr]:
        db = self.Session()
        connected_lawyers = []
        connections = (
            db.query(ImmigrantLawyerConnection)
            .filter(
                ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
                ImmigrantLawyerConnection.connected_boolean == True,
            )
            .all()
        )
        if connections:
            for lawyer in connections:
                connected_lawyers.append(lawyer.lawyer_email)
        db.close()
        return connected_lawyers

    def retrieve_connected_lawyers(
        self, immigrant_email: EmailStr, case_id: str = None, only_emails: bool = False
    ) -> list[dict[str, Union[str, bool, list[str]]]]:
        db = self.Session()
        lawyers = []
        connected_lawyers = (
            db.query(ImmigrantLawyerConnection)
            .filter(
                ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
                ImmigrantLawyerConnection.connected_boolean == True,
            )
            .all()
        )
        if connected_lawyers:
            for connected_lawyer in connected_lawyers:
                if connected_lawyer.lawyer_case_ids is not None:
                    lawyer = self.get_lawpersonnel(connected_lawyer.lawyer_email)
                    if lawyer:
                        lawyers.append(
                            {
                                "lawyer": lawyer.email,
                                "Point of Contact": f"{lawyer.full_legal_name}",
                                "Law Firm Name": getattr(lawyer, "law_firm_name", None),
                                "Experience": getattr(lawyer, "experience", None),
                                "Expertise": getattr(lawyer, "specialty", None),
                                "Main Office": getattr(
                                    lawyer, "professional_address", None
                                ),
                                "Phone Number": getattr(lawyer, "contact_number", None),
                                "Image link": getattr(lawyer, "profile_picture", None),
                                "Email Address": getattr(lawyer, "email", None),
                                "Verified": (
                                    getattr(lawyer, "verified", False)
                                    if hasattr(lawyer, "verified")
                                    else False
                                ),
                                "case_id": connected_lawyer.lawyer_case_ids,
                            }
                        )
        if case_id is not None:
            db.close()
            result = [
                lawyer["lawyer"] for lawyer in lawyers if case_id in lawyer["case_id"]
            ]
            return result[0] if len(result) > 0 else None
        elif only_emails:
            db.close()
            return [lawyer["lawyer"] for lawyer in lawyers]
        else:
            db.close()
            return lawyers

    def check_if_connected_lawyers(self, immigrant_email: EmailStr) -> bool:
        db = self.Session()
        connected_lawyers = (
            db.query(ImmigrantLawyerConnection)
            .filter(
                ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
                ImmigrantLawyerConnection.connected_boolean == True,
            )
            .all()
        )
        if connected_lawyers:
            db.close()
            return True
        else:
            db.close()
            return False

    def save_lawyer(self, immigrant_email: EmailStr, lawyer_email: EmailStr) -> None:
        db = self.Session()
        saved_lawyer = (
            db.query(ImmigrantLawyerConnection)
            .filter(
                ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
                ImmigrantLawyerConnection.lawyer_email == lawyer_email.lower(),
                ImmigrantLawyerConnection.saved_boolean == True,
            )
            .first()
        )
        if not saved_lawyer:
            saved_lawyer = ImmigrantLawyerConnection(
                immigrant_email=immigrant_email.lower(),
                lawyer_email=lawyer_email.lower(),
                saved_boolean=True,
            )
            db.add(saved_lawyer)
            db.commit()
        db.close()

    def unsave_lawyer(self, immigrant_email: EmailStr, lawyer_email: EmailStr) -> None:
        db = self.Session()
        saved_lawyer = (
            db.query(ImmigrantLawyerConnection)
            .filter(
                ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
                ImmigrantLawyerConnection.lawyer_email == lawyer_email.lower(),
                ImmigrantLawyerConnection.saved_boolean == True,
            )
            .first()
        )
        if saved_lawyer:
            db.delete(saved_lawyer)
        db.commit()
        db.close()

    def get_saved_lawyers(self, immigrant_email: EmailStr) -> list[EmailStr]:
        db = self.Session()
        all_saved = set([])
        saved_lawyers = (
            db.query(ImmigrantLawyerConnection)
            .filter(
                ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
                ImmigrantLawyerConnection.saved_boolean == True,
            )
            .all()
        )
        if saved_lawyers:
            for saved_lawyer in saved_lawyers:
                all_saved.add(saved_lawyer.lawyer_email)

        db.close()
        return list(all_saved)

    def retrieve_lawyer_connections(self, lawyer_email: EmailStr) -> list[ImmigrantLawyerConnection]:
        db = self.Session()
        lawyer_connections = db.query(ImmigrantLawyerConnection).filter(ImmigrantLawyerConnection.lawyer_email==lawyer_email.lower(), ImmigrantLawyerConnection.connected_boolean==True).all()
        if lawyer_connections:
            db.close()
            return [lawyer_conn for lawyer_conn in lawyer_connections]
        db.close()
        return []

    def get_connected_lawyer_cases(
        self, lawyer_email: EmailStr, immigrant_email: EmailStr
    ) -> list[str]:
        db = self.Session()
        lawyer_cases = []
        lawyer_connection = (
            db.query(ImmigrantLawyerConnection)
            .filter(
                ImmigrantLawyerConnection.lawyer_email == lawyer_email.lower(),
                ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
                ImmigrantLawyerConnection.connected_boolean == True,
            )
            .first()
        )
        if lawyer_connection and lawyer_connection.lawyer_case_ids is not None:
            lawyer_cases = lawyer_connection.lawyer_case_ids

        db.close()
        return lawyer_cases

    def disconnect_lawyer_connection(
        self, lawyer_email: EmailStr, immigrant_email: EmailStr
    ) -> None:
        db = self.Session()
        lawyer_connections = (
            db.query(ImmigrantLawyerConnection)
            .filter(
                ImmigrantLawyerConnection.lawyer_email == lawyer_email.lower(),
                ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
                ImmigrantLawyerConnection.connected_boolean == True,
            )
            .all()
        )
        if lawyer_connections:
            for connection in lawyer_connections:
                if connection.saved_boolean:
                    connection.connected_boolean = False
                    db.commit()
                    db.refresh(connection)
                else:
                    db.delete(connection)
                    db.commit()
        db.close()

    def delete_immigrant_connections(self, immigrant_email: EmailStr) -> None:
        db = self.Session()
        connections = (
            db.query(ImmigrantLawyerConnection)
            .filter(
                ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower()
            )
            .all()
        )
        if connections:
            for connection in connections:
                db.delete(connection)
            db.commit()
        db.close()

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
        db = self.Session()
        exist_invitation = (
            db.query(Invitations)
            .filter(
                Invitations.invited_email == invited_email.lower(),
                Invitations.invited_type == invited_type,
                Invitations.invitee_email == invitee_email,
            )
            .first()
        )
        invitation_map = {
            "invited_client": Invitations(
                invited_type=invited_type,
                invited_email=invited_email.lower(),
                invitee_email=invitee_email.lower(),
                case_type=case_type,
            ),
            "pending_case": Invitations(
                invited_type=invited_type,
                invited_email=invited_email.lower(),
                invitee_email=invitee_email.lower(),
                case_id=case_id,
                client_number=client_number,
                client_address=client_address,
                case_name=case_name,
                case_description=case_description,
                case_type=case_type,
                assignees=assignees,
            ),
            "pending_client": Invitations(
                invited_type=invited_type,
                invited_email=invited_email.lower(),
                invitee_email=invitee_email.lower(),
                client_number=client_number,
                client_address=client_address,
                case_type=case_type,
            ),
            "invited_external_lawyer": Invitations(
                invited_type=invited_type,
                invited_email=invited_email.lower(),
                invitee_email=invitee_email.lower(),
                client_number=client_number,
                client_address=client_address,
                case_type=case_type,
            ),
            "invited_to_case": Invitations(
                invited_type=invited_type,
                invited_email=invited_email.lower(),
                invitee_email=invitee_email.lower(),
                member_role=member_role,
                member_permissions=member_permissions,
                case_id=case_id,
            ),
            "invited_to_team": Invitations(
                invited_type=invited_type,
                invited_email=invited_email.lower(),
                invitee_email=invitee_email.lower(),
                member_role=member_role,
                member_permissions=member_permissions,
            ),
            "refered_user": Invitations(
                invited_type=invited_type,
                invited_email=invited_email.lower(),
                invitee_email=invitee_email.lower(),
            ),
        }
        invite_success = False
        if not exist_invitation:
            new_invitation = invitation_map[invited_type]
            db.add(new_invitation)
            db.commit()
            invite_success = True
        db.close()
        return invite_success

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
        db = self.Session()
        if invited_email:
            invitations = (
                db.query(Invitations)
                .filter(
                    Invitations.invited_email == invited_email.lower(),
                    Invitations.invited_type == invited_type,
                )
                .all()
            )
        elif invitee_email:
            invitations = (
                db.query(Invitations)
                .filter(
                    Invitations.invitee_email == invitee_email.lower(),
                    Invitations.invited_type == invited_type,
                )
                .all()
            )
        else:
            return HTTPException(
                status_code=400,
                detail="Either invited_email or invitee_email must be provided.",
            )
        invitation_data = {
            "invited_client": (
                {
                    invitation.invitee_email: invitation.case_type
                    for invitation in invitations
                }
                if invitations
                else None
            ),
            "pending_case": (
                [
                    {
                        "case_id": invitation.case_id,
                        "lawyer_email": invitation.invitee_email,
                        "client_email": invitation.invited_email,
                        "client_contact": invitation.client_number,
                        "client_address": invitation.client_address,
                        "case_name": invitation.case_name,
                        "case_description": invitation.case_description,
                        "case_type": invitation.case_type,
                        "assignees": invitation.assignees,
                    }
                    for invitation in invitations
                ]
                if invitations
                else None
            ),
            "pending_client": (
                {
                    invitation.invited_email: {
                        "client_number": invitation.client_number,
                        "client_address": invitation.client_address,
                        "case_type": invitation.case_type,
                    }
                    for invitation in invitations
                }
                if invitations
                else {}
            ),
            "invited_external_lawyer": (
                {
                    invitation.invitee_email: {
                        "client_number": invitation.client_number,
                        "client_address": invitation.client_address,
                        "case_type": invitation.case_type,
                    }
                    for invitation in invitations
                }
                if invitations
                else {}
            ),
            "invited_to_case": (
                {
                    invitation.invitee_email: {
                        "role": invitation.member_role,
                        "permissions": invitation.member_permissions,
                        "case_id": invitation.case_id,
                    }
                    for invitation in invitations
                }
                if invitations
                else {}
            ),
            "invited_to_team": (
                {
                    invitation.invitee_email: {
                        "role": invitation.member_role,
                        "permissions": invitation.member_permissions,
                    }
                    for invitation in invitations
                }
                if invitations
                else {}
            ),
            "refered_user": (
                [invitation.invitee_email for invitation in invitations][0]
                if invitations
                else None
            ),
        }
        result = invitation_data[invited_type]
        if result == []:
            result = None
        db.close()
        return result

    def delete_invitation_data(
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
        case_id: str = None,
        invitee_email: EmailStr = None,
    ) -> None:
        db = self.Session()
        inviteee_email = invitee_email.lower() if invitee_email else None
        invitation_data = {
            "invited_client": db.query(Invitations)
            .filter(
                Invitations.invited_email == invited_email.lower(),
                Invitations.invited_type == invited_type,
            )
            .first(),
            "pending_case": db.query(Invitations)
            .filter(
                Invitations.invited_type == invited_type, Invitations.case_id == case_id
            )
            .first(),
            "pending_client": db.query(Invitations)
            .filter(
                Invitations.invited_type == invited_type,
                Invitations.invited_email == invited_email.lower(),
                Invitations.invitee_email == inviteee_email,
            )
            .first(),
            "invited_external_lawyer": db.query(Invitations)
            .filter(
                Invitations.invited_type == invited_type,
                Invitations.invited_email == invited_email.lower(),
                Invitations.invitee_email == inviteee_email,
            )
            .first(),
            "invited_to_case": db.query(Invitations)
            .filter(
                Invitations.invited_type == invited_type,
                Invitations.invited_email == invited_email.lower(),
                Invitations.invitee_email == inviteee_email,
                Invitations.case_id == case_id,
            )
            .first(),
            "invited_to_team": db.query(Invitations)
            .filter(
                Invitations.invited_type == invited_type,
                Invitations.invited_email == invited_email.lower(),
                Invitations.invitee_email == inviteee_email,
            )
            .first(),
            "refered_user": db.query(Invitations)
            .filter(
                Invitations.invited_email == invited_email.lower(),
                Invitations.invited_type == invited_type,
            )
            .first(),
        }
        invitation = invitation_data[invited_type]
        if invitation:
            db.delete(invitation)
            db.commit()
        db.close()

    def remove_case_from_invitation(self, case_id: str) -> None:
        db = self.Session()
        invitations = db.query(Invitations).filter(Invitations.case_id == case_id).all()
        if invitations:
            for invitation in invitations:
                db.delete(invitation)
            db.commit()
        db.close()

    def retrieve_pending_lawyers(self, immigrant_email: EmailStr) -> list[EmailStr]:
        db = self.Session()
        pending_lawyers = db.query(Invitations.invited_email).filter(Invitations.invited_type=="pending_client", Invitations.invitee_email == immigrant_email).all()
        if pending_lawyers:
            return [lawyer[0] for lawyer in pending_lawyers]
        return []

    def retrieve_pending_client(self, lawyer_email: EmailStr) -> list[EmailStr]:
        db = self.Session()
        pending_clients = (
            db.query(Invitations.invited_email)
            .filter(
                Invitations.invited_type == "invited_client",
                Invitations.invitee_email == lawyer_email,
            )
            .all()
        )
        if pending_clients:
            return [client[0] for client in pending_clients]
        return []

    def remove_invitation_notification(self, immigrant_email: EmailStr) -> None:
        # db = self.Session()

        # notification_alerts = (
        #     db.query(NotificationAlerts)
        #     .filter(
        #         NotificationAlerts.sender == immigrant_email.lower(),
        #         NotificationAlerts.type == "connection",
        #     )
        #     .all()
        # )
        # if notification_alerts:
        #     for alert in notification_alerts:
        #         if "Refered user" in alert.content and alert.target_id == {}:
        #             db.delete(alert)
        #     db.commit()
        # db.close()
        # TODO: Connect to User Services
        pass

    def remove_immigrant_invitations(self, immigrant_email: EmailStr) -> None:
        db = self.Session()
        invitations = db.query(Invitations).filter(
            or_(
                Invitations.invited_email == immigrant_email.lower(),
                Invitations.invitee_email == immigrant_email.lower(),
            )
        )
        if invitations:
            for invitation in invitations:
                db.delete(invitation)
            db.commit()
        self.remove_immigrant_invitations(immigrant_email)
        db.close()

    def retrieve_sent_intake_cases(self, case_ids: str) -> list[ClientIntake]:
        db = self.Session()
        intakes = db.query(ClientIntake.case_id).filter(ClientIntake.case_id.in_(case_ids), ClientIntake.date_sent.isnot(None)).all()
        if intakes:
            return [intake[0] for intake in intakes]
        return []

    def add_client_intake(
        self,
        lawyer_email: EmailStr,
        client_email: EmailStr,
        case_id: str,
        case_type: str,
        intake_form_id: str,
        date_sent: date,
        form_url: str,
    ) -> None:
        form_url.replace(" ", "+")
        db = self.Session()
        exist_intake = (
            db.query(ClientIntake)
            .filter(
                ClientIntake.lawyer_email == lawyer_email,
                ClientIntake.client_email == client_email,
                ClientIntake.case_id == case_id,
            )
            .first()
        )
        if not exist_intake:
            new_client_intake = ClientIntake(
                lawyer_email=lawyer_email,
                client_email=client_email,
                case_id=case_id,
                case_type=case_type,
                intake_form_id=intake_form_id,
                date_sent=date_sent,
                intake_form_url=form_url,
            )
            db.add(new_client_intake)
            db.commit()
        else:
            exist_intake.intake_form_id = intake_form_id
            exist_intake.date_sent = date_sent
            exist_intake.intake_form_url = form_url
            db.commit()
        db.close()

    def update_client_intake(
        self, case_id: str, date_signed: date, handshake_id: str, form_url: str
    ) -> str:
        form_url.replace(" ", "+")
        db = self.Session()
        case_type = None
        client_intake = (
            db.query(ClientIntake).filter(ClientIntake.case_id == case_id).first()
        )
        form_url.replace(" ", "+")
        if client_intake:
            case_type = client_intake.case_type
            client_intake.date_signed = date_signed
            client_intake.handshake_id = handshake_id
            client_intake.intake_form_url = form_url
            db.commit()
            db.refresh(client_intake)
        db.close()
        return case_type

    def check_intake_md5(self, file_md5: str, lawyer_email: EmailStr) -> bool:
        db = self.Session()
        is_exist = False
        all_forms = (
            db.query(LawyerForms).filter(LawyerForms.lawyer_email == lawyer_email).all()
        )
        if all_forms:
            for form in all_forms:
                if form.form_md5 == file_md5:
                    is_exist = True
                break
        return is_exist

    def upload_intake_form(
        self, file_url: str, lawyer_email: EmailStr, filename: str, file_md5: str
    ) -> dict[str, Union[str, date]]:
        db = self.Session()
        date = datetime.now(tz=timezone.utc).date()
        new_intake_form = LawyerForms(
            lawyer_email=lawyer_email,
            form_name=filename,
            form_url=file_url,
            form_md5=file_md5,
            upload_date=date,
        )
        db.add(new_intake_form)
        db.commit()
        db.refresh(new_intake_form)

        return_value = {
            "form_id": new_intake_form.uuid,
            "filename": new_intake_form.form_name,
            "form_url": new_intake_form.form_url,
            "last_case_type": new_intake_form.last_used_case_type,
            "upload_date": new_intake_form.upload_date,
        }
        db.close()
        return return_value

    def delete_intake_form(
        self, lawyer_email: EmailStr, form_id: str
    ) -> tuple[bool, str]:
        db = self.Session()
        form = (
            db.query(LawyerForms)
            .filter(
                LawyerForms.lawyer_email == lawyer_email, LawyerForms.uuid == form_id
            )
            .first()
        )
        is_success = False
        form_url = None
        if form:
            form_url = form.form_url
            db.delete(form)
            db.commit()
            is_success = True
        db.close()
        return is_success, form_url

    def retrieve_forms(
        self, lawyer_email: EmailStr
    ) -> list[dict[str, Union[str, date]]]:
        db = self.Session()
        all_intakes = []
        all_forms = (
            db.query(LawyerForms).filter(LawyerForms.lawyer_email == lawyer_email).all()
        )
        if all_forms:
            for form in all_forms:
                all_intakes.append(
                    {
                        "form_id": form.uuid,
                        "filename": form.form_name,
                        "form_url": form.form_url,
                        "last_case_type": form.last_used_case_type,
                        "upload_date": form.upload_date,
                    }
                )
        db.close()
        return all_intakes

    def update_intake_form(
        self,
        lawyer_email: EmailStr,
        form_id: str,
        case_type: str,
        date_used: date,
        form_url: str,
    ) -> None:
        form_url.replace(" ", "+")
        db = self.Session()
        form = (
            db.query(LawyerForms)
            .filter(
                LawyerForms.lawyer_email == lawyer_email, LawyerForms.uuid == form_id
            )
            .first()
        )
        if form:
            form.last_used_case_type = case_type
            form.last_used = date_used
            form.form_url = form_url
            db.commit()
        db.close()

    def retrieve_intake_form(
        self, intake_form_id: str
    ) -> tuple[Union[HttpUrl, None], Union[str, None]]:
        db = self.Session()
        intake_form = (
            db.query(LawyerForms).filter(LawyerForms.uuid == intake_form_id).first()
        )
        form_url = None
        form_name = None
        form_owner = None
        if intake_form:
            form_url = intake_form.form_url
            form_name = intake_form.form_name
            form_owner = intake_form.lawyer_email
        db.close()
        return form_url, form_name, form_owner

    def retrieve_intake_form_ids(self, lawyer_email: EmailStr) -> list[str]:
        db = self.Session()
        all_form_ids = db.query(LawyerForms.uuid).filter(LawyerForms.lawyer_email == lawyer_email).all()
        if all_form_ids:
            return [form_id[0] for form_id in all_form_ids]
        return []

    def retrieve_all_form_ids(self) -> list[str]:
        db = self.Session()
        all_form_ids = (
            db.query(LawyerForms.uuid)
            .all()
        )
        if all_form_ids:
            return [form_id[0] for form_id in all_form_ids]
        return []

    def retrieve_lawyer_form_url(self, form_id: str) -> list[str]:
        db = self.Session()
        all_form_urls = db.query(LawyerForms.form_url).filter(LawyerForms.uuid == form_id).all()
        if all_form_urls:
            return [form_url[0] for form_url in all_form_urls]
        return []

    def retrieve_case_lawyer(self, case_id: str) -> EmailStr:
        # db = self.Session()
        # lawyer_email = (
        #     db.query(AllCases.lawyer_email).filter(AllCases.case_id == case_id).first()[0]
        # )
        # return lawyer_email
        # TODO: connect to case management
        pass

    def add_new_connection_request(self, message: str, sender_email: EmailStr, recipient_email: EmailStr) -> str:
        db = self.Session()
        new_message = ConnectionRequests(
            message=message,
            sender_email=sender_email,
            recipient_email=recipient_email
        )
        db.add(new_message)
        db.commit()
        message_id = new_message.id
        db.close()
        return message_id

    def retrieve_all_connection_requests(self) -> list[dict[str, str]]:
        db = self.Session()
        all_conn = db.query(ConnectionRequests).filter(ConnectionRequests).all()
        all_connection_requests = []
        if all_conn:
            for connection_request in all_conn:
                all_connection_requests.append({
                    "date_sent": connection_request.timestamp,
                    "status": connection_request.status,
                    "date_status_change": connection_request.status_changed if connection_request.status_changed else ""
                })
        db.close()
        return all_connection_requests

    def retrieve_specific_connection_request(self, connection_id: str) -> ConnectionRequests:
        db = self.Session()
        connection_request = db.query(ConnectionRequests).filter(ConnectionRequests.id == connection_id).first()
        if connection_request:
            db.close()
            return connection_request
        db.close()

    def retrieve_all_sent_requests(self, sender_email: EmailStr) -> list[ConnectionRequests]:
        db = self.Session()
        all_sent = db.query(ConnectionRequests).filter(ConnectionRequests.sender_email == sender_email).all()
        if all_sent:
            db.close()
            return [conn_req for conn_req in all_sent]
        db.close()

    def retrieve_all_recieved_requests(
        self, recipient_email: EmailStr
    ) -> list[ConnectionRequests]:
        db = self.Session()
        all_rec = (
            db.query(ConnectionRequests)
            .filter(ConnectionRequests.recipient_email == recipient_email)
            .all()
        )
        if all_rec:
            db.close()
            return [conn_req for conn_req in all_rec]
        db.close()

    def add_new_approved_request(
        self, message: str, sender_email: EmailStr, recipient_email: EmailStr
    ) -> None:
        db = self.Session()
        new_message = ConnectionRequests(
            message=message, sender_email=sender_email, recipient_email=recipient_email, status="Approved"
        )
        db.add(new_message)
        db.commit()
        db.close()

    def change_connection_request_status(
        self, connection_id: str, new_status: Literal["Pending", "Approved", "Denied"]
    ) -> ConnectionRequests:
        db = self.Session()
        connection_request = (
            db.query(ConnectionRequests)
            .filter(ConnectionRequests.id == connection_id)
            .first()
        )
        if connection_request:
            connection_request.status = new_status
            db.commit()
            db.refresh(connection_request)
            db.close()
            return connection_request
        db.close()

    def retrieve_connection_ids(self) -> list[str]:
        db = self.Session()
        all_conn_ids = db.query(ConnectionRequests.id).all()
        if all_conn_ids:
            db.close()
            return [all_conn_id[0] for all_conn_id in all_conn_ids]
        db.close()
        return []

    def delete_all_user_requests(self, lawyer_email: EmailStr, immigrant_email: EmailStr) -> None:
        db = self.Session()
        all_requests = db.query(ConnectionRequests).filter(
            or_(
                (ConnectionRequests.recipient_email == lawyer_email.lower())
                & (ConnectionRequests.sender_email == immigrant_email.lower()),
                (ConnectionRequests.sender_email == lawyer_email.lower())
                & (ConnectionRequests.recipient_email == immigrant_email.lower()),
            )
        ).all()
        if all_requests:
            for request in all_requests:
                db.delete(request)
            db.commit()
        db.close()

    def check_existing_case(
        self,
        lawyer_email: EmailStr,
        immigrant_email: EmailStr,
        case_type: str = Literal[
            "nonimmigrant_worker",
            "employment_auth",
            "alien_rel",
            "asylum_removal",
            "naturalization",
        ],
    ) -> str:
        # db = self.Session()
        # case_id = None
        # exist_case = (
        #     db.query(AllCases)
        #     .filter(
        #         AllCases.lawyer_email == lawyer_email.lower(),
        #         AllCases.client_email == immigrant_email.lower(),
        #         AllCases.case_type == case_type.lower(),
        #     )
        #     .first()
        # )
        # if exist_case:
        #     case_id = exist_case.case_id
        # db.close()
        # return case_id
        # TODO: Connect with case management service
        pass

    def create_case(
        self,
        lawyer_email: EmailStr,
        case_details: dict[str, EmailStr, Union[str, list[EmailStr]]],
    ) -> None:
        # db = self.Session()
        # self.update_clients(
        #     lawyer_email,
        #     case_details["client_email"],
        #     case_details["client_number"],
        #     case_details["client_address"],
        # )
        # new_case = AllCases(
        #     case_id=case_details["case_id"],
        #     lawyer_email=lawyer_email.lower(),
        #     client_email=case_details["client_email"].lower(),
        #     case_name=case_details["case_name"],
        #     assignee_list=[
        #         assignee.lower() for assignee in case_details["assignee_list"]
        #     ],
        #     case_description=case_details["description"],
        #     case_type=case_details["case_type"],
        # )

        # db.add(new_case)
        # db.commit()
        # db.close()
        # TODO: Connect with case management
        pass

    def add_task(
        self,
        task_details: dict[str, Union[str, list[str], list[EmailStr], datetime]],
        lawyer_email: EmailStr,
    ) -> None:
        # db = self.Session()
        # task_documents = [
        #     document.replace(" ", "+") for document in task_details["document_list"]
        # ]
        # task_details["document_list"] = task_documents
        # if "id" not in task_details:
        #     task_details["id"] = generate_uuid()

        # case = (
        #     db.query(AllCases)
        #     .filter(AllCases.case_id == task_details["case_id"])
        #     .first()
        # )
        # if case:
        #     # print("Creating new task")
        #     new_task = AllTasks(
        #         uuid=task_details["id"],
        #         lawyer_email=lawyer_email.lower(),
        #         task_name=task_details["name"],
        #         task_visibility=task_details["visibility"],
        #         case_name=task_details["case_name"],
        #         case_id=task_details["case_id"],
        #         task_assignees=[
        #             assignee.lower() for assignee in task_details["assignee_list"]
        #         ],
        #         task_status=task_details["status"],
        #         task_deadline=task_details["deadline"],
        #         task_documents=task_details["document_list"],
        #         task_description=task_details["description"],
        #     )
        #     # print(new_task)
        #     db.add(new_task)
        #     db.commit()
        #     db.refresh(new_task)
        # db.close()
        # TODO: connect with case management
        pass

    def add_tasks_to_case(self, task_list: list[str], case_id: str) -> None:
        # db = self.Session()
        # case = db.query(AllCases).filter(AllCases.case_id == case_id).first()
        # if case:
        #     prev_tasklist = []
        #     if case.task_list is not None:
        #         prev_tasklist.extend(case.task_list)
        #     new_tasklist = [task for task in task_list if task not in prev_tasklist]
        #     prev_tasklist.extend(new_tasklist)
        #     case.task_list = prev_tasklist
        #     db.commit()
        #     db.refresh(case)
        # db.close()
        # TODO: Connect with case management
        pass

    def remove_recommended_lawpersonnel(
        self, immigrant_email, lawpersonnel_email
    ) -> bool:
        # TODO: connect with ai agent module
        pass

    def remove_external_lawyer(self, email: EmailStr) -> None:
        # db = self.Session()
        # external_lawyer = self.get_external_lawyer(email)
        # if external_lawyer:
        #     db.delete(external_lawyer)
        #     db.commit()
        # db.close()
        # TODO: connect with user management
        pass

    def remove_lawyer_from_recommendations(
        self, client_email: EmailStr, lawyer_email: EmailStr
    ) -> None:
        # db = self.Session()
        # lawyer_recommendations = (
        #     db.query(LawyerRecommendations)
        #     .filter(LawyerRecommendations.client_email == client_email.lower())
        #     .first()
        # )
        # if lawyer_recommendations:
        #     registered_lawyers = [
        #         lawyer
        #         for lawyer in lawyer_recommendations.registered_lawyers
        #         if lawyer != lawyer_email.lower()
        #     ]
        #     unregistered_lawyers = [
        #         lawyer
        #         for lawyer in lawyer_recommendations.unregistered_lawyers
        #         if lawyer != lawyer_email.lower()
        #     ]
        #     lawyer_recommendations.registered_lawyers = registered_lawyers
        #     lawyer_recommendations.unregistered_lawyers = unregistered_lawyers
        #     db.commit()
        #     db.refresh(lawyer_recommendations)
        # db.close()
        # TODO: Connect with ai agents service
        pass

    def add_recent_action(
        self, lawyer_email: EmailStr, case_id: str, action: str, actor: str, role: str
    ) -> None:
        # db = self.Session()
        # action_time = datetime.now(timezone.utc)
        # new_action = CaseRecentActions(
        #     lawyer_email=lawyer_email.lower(),
        #     lawyer_case=case_id,
        #     action=action,
        #     actor=actor,
        #     role=role,
        #     action_time=action_time,
        # )

        # db.add(new_action)
        # db.commit()
        # db.close()
        # TODO: connect with case management
        pass

    def check_case(self, case_id: str) -> AllCases:
        # db = self.Session()
        # case = db.query(AllCases).filter(AllCases.case_id == case_id).first()
        # if case:
        #     return case
        # db.close()
        # return None
        # TODO: Connect to case management
        pass

    def retrieve_case_specific_tasks(
        self, lawyer_email: EmailStr, case_id: str
    ) -> list[dict[str, Union[str, list[str], list[EmailStr], datetime]]]:
        # db = self.Session()
        # all_tasks = []
        # today = datetime.now(timezone.utc).date()

        # case = (
        #     db.query(AllCases)
        #     .filter(
        #         AllCases.lawyer_email == lawyer_email.lower(),
        #         AllCases.case_id == case_id,
        #     )
        #     .first()
        # )

        # if case and case.task_list is not None:
        #     for task_id in case.task_list:
        #         task = self.retrieve_task(lawyer_email, task_id)
        #         if task:
        #             all_tasks.append(task)

        # completed_tasks = [task for task in all_tasks if task.get("status") == "Done"]
        # pending_tasks = [task for task in all_tasks if task.get("status") != "Done"]

        # for task in pending_tasks:
        #     if task.get("deadline") and isinstance(task.get("deadline"), str):
        #         task["deadline_date"] = datetime.strptime(
        #             task["deadline"], "%Y-%m-%d"
        #         ).date()
        #     else:
        #         task["deadline_date"] = datetime.max.date()

        # for task in completed_tasks:
        #     if task.get("task_completed_date") and isinstance(
        #         task.get("task_completed_date"), str
        #     ):
        #         task["completed_date"] = datetime.strptime(
        #             task["task_completed_date"], "%Y-%m-%d"
        #         ).date()
        #     if task.get("deadline") and isinstance(task.get("deadline"), str):
        #         task["completed_date"] = datetime.strptime(
        #             task["deadline"], "%Y-%m-%d"
        #         ).date()
        #     else:
        #         task["completed_date"] = datetime.max.date()

        # pending_tasks.sort(key=lambda x: (x.get("deadline_date") - today).days)
        # completed_tasks.sort(key=lambda x: (x.get("completed_date") - today).days)
        # sorted_tasks = pending_tasks + completed_tasks
        # for task in sorted_tasks:
        #     if "deadline_date" in task:
        #         del task["deadline_date"]
        #     if "completed_date" in task:
        #         del task["completed_date"]
        # db.close()
        # return sorted_tasks
        # TODO: Connect with case management
        pass

    def update_task_status(
        self,
        lawyer_email: EmailStr,
        task_id: str,
        status: str = Literal["To-Do", "In-Progress", "In-Review", "Done", "Rejected"],
    ) -> tuple[int, str, str]:
        # db = self.Session()
        # task = (
        #     db.query(AllTasks)
        #     .filter(
        #         AllTasks.lawyer_email == lawyer_email.lower(), AllTasks.uuid == task_id
        #     )
        #     .first()
        # )
        # success = 0
        # task_name = None
        # case_id = None
        # if task:
        #     task.task_status = status
        #     if status == "Done":
        #         task.task_completed_date = datetime.now(timezone.utc).date().isoformat()
        #     success = 1
        #     task_name = task.task_name
        #     case_id = task.case_id
        #     db.commit()
        #     db.refresh(task)

        # db.close()
        # return success, task_name, case_id
        # TODO: connect with case management
        pass

    def retrieve_case_name(self, lawyer_email: EmailStr, case_id: str) -> str:
        # db = self.Session()
        # case_name = None
        # case = (
        #     db.query(AllCases)
        #     .filter(
        #         AllCases.lawyer_email == lawyer_email.lower(),
        #         AllCases.case_id == case_id,
        #     )
        #     .first()
        # )
        # if case:
        #     case_name = case.case_name
        # db.close()
        # return case_name
        # TODO: connect with case management
        pass
