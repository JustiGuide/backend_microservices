import json
import os
from typing import Any, Union, Literal
from pydantic import EmailStr
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    LargeBinary,
    String,
    Text,
    Boolean,
    create_engine,
    func,
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


class AllTasks(Base):
    __tablename__ = "all_tasks"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawyer_email = Column(EncryptedText, nullable=False, index=True)
    task_name = Column(EncryptedText, nullable=False)
    task_visibility = Column(Text, nullable=False)
    case_name = Column(EncryptedText, nullable=False)
    case_id = Column(String(7), nullable=False)
    task_assignees = Column(EncryptedText, nullable=True)
    task_status = Column(Text, nullable=False, default="To-Do")
    task_completed_date = Column(Text, nullable=True)
    task_deadline = Column(Text, nullable=False)
    task_documents = Column(EncryptedText, nullable=True)
    task_description = Column(EncryptedText, nullable=True)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "lawyer_email": self.lawyer_email,
            "task_name": self.task_name,
            "task_visibility": self.task_visibility,
            "case_name": self.case_name,
            "case_id": self.case_id,
            "task_assignees": self.task_assignees,
            "task_status": self.task_status,
            "task_completed_date": self.task_completed_date,
            "task_deadline": self.task_deadline,
            "task_documents": self.task_documents,
            "task_description": self.task_description,
        }

    def __repr__(self):
        return f"<AllTasks(uuid={self.uuid}, lawyer_email={self.lawyer_email}, task_name={self.task_name}, task_visibility={self.task_visibility}, case_name={self.case_name}, case_id={self.case_id}, task_assignees={self.task_assignees}, task_status={self.task_status}, task_completed_date={self.task_completed_date}, task_deadline={self.task_deadline}, task_documents={self.task_documents}, task_description={self.task_description})>"


class CaseRecentActions(Base):
    __tablename__ = "case_actions"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawyer_email = Column(EncryptedText, nullable=False, index=True)
    lawyer_case = Column(String(7), nullable=False, index=True)
    action = Column(EncryptedText, nullable=False)
    actor = Column(EncryptedText, nullable=False)
    role = Column(String(50), nullable=False)
    action_time = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "lawyer_email": self.lawyer_email,
            "lawyer_case": self.lawyer_case,
            "action": self.action,
            "actor": self.actor,
            "role": self.role,
            "action_time": self.action_time,
        }

    def __repr__(self):
        return f"<CaseRecentActions(uuid={self.uuid}, lawyer_email={self.lawyer_email}, lawyer_case={self.lawyer_case}, action={self.action}, actor={self.actor}, role={self.role}, action_time={self.action_time})>"


class LawyerTeams(Base):
    __tablename__ = "lawyer_teams"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    member_role = Column(String(50), nullable=False)
    member_email = Column(EncryptedText, nullable=False)
    lawyer_email = Column(EncryptedText, nullable=False)
    lawyer_cases = Column(EncryptedText, nullable=False, default=[])
    member_permissions = Column(JSON, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "member_role": self.member_role,
            "member_email": self.member_email,
            "lawyer_email": self.lawyer_email,
            "lawyer_cases": self.lawyer_cases,
            "member_permissions": self.member_permissions,
        }

    def __repr__(self):
        return f"<LawyerTeams(uuid={self.uuid}, member_role={self.member_role}, member_email={self.member_email}, lawyer_email={self.lawyer_email}, lawyer_cases={self.lawyer_cases}, member_permissions={self.member_permissions})>"


class CaseTeams(Base):
    __tablename__ = "case_teams"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawyer_email = Column(EncryptedText, nullable=False)
    member_name = Column(EncryptedText, nullable=False)
    member_type = Column(String(50), nullable=False)
    member_email = Column(EncryptedText, nullable=False)
    lawyer_case = Column(EncryptedText, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "lawyer_email": self.lawyer_email,
            "member_name": self.member_name,
            "member_type": self.member_type,
            "member_email": self.member_email,
            "lawyer_case": self.lawyer_case,
        }

    def __repr__(self):
        return f"<CaseTeams(uuid={self.uuid}, lawyer_email={self.lawyer_email}, member_name={self.member_name}, member_type={self.member_type}, member_email={self.member_email}, lawyer_case={self.lawyer_case})>"


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

    def retrieve_lawpersonnel_case_subs(self, case_ids: list[str]) -> dict[str, bool]:
        # TODO: connect with billing module
        pass

    def retrieve_lawpersonnel_intakes(self, case_ids: list[str]) -> list[str]:
        # TODO: connct with relationship module
        pass

    def retrieve_all_clients(
        self, client_emails: list[EmailStr]
    ) -> tuple[dict[str, dict[str, Union[str, str]]], dict[str, dict[str, str]]]:
        # TODO: connect with relationship module (phone & address) & user management module (full name, profile pic)
        pass

    def retrieve_client_details(
            self, lawyer_email: EmailStr, client_email: EmailStr
    ) -> dict[str, Union[str, str]]:
        # TODO: connect with relationship module
        pass

    def retrieve_all_assignees(self, assignee_emails: list[EmailStr]) -> dict[str, dict[str, str]]:
        for assignee in assignee_emails:
            assigned_user = self.get_lawpersonnel(assignee)

        # TODO: complete the function
        pass

    def retrieve_all_cases(
        self, lawyer_email: EmailStr
    ) -> dict[str, dict[str, Union[str, EmailStr, list[EmailStr], list[str], bool]]]:
        db = self.Session()
        all_cases = {}

        cases = (
            db.query(AllCases)
            .filter(AllCases.lawyer_email == lawyer_email.lower())
            .all()
        )

        if not cases:
            db.close()
            return all_cases

        case_ids = [case.case_id for case in cases]
        client_emails = [case.client_email for case in cases]
        assignee_emails = set()
        for case in cases:
            if case.assignee_list:
                assignee_emails.update(case.assignee_list)

        clients_details, users_data = self.retrieve_all_clients(client_emails)
        law_personnel_data = self.retrieve_all_assignees(assignee_emails)
        intake_sent = self.retrieve_lawpersonnel_intakes(case_ids)
        case_paid = self.retrieve_lawpersonnel_case_subs(case_ids)

        for case in cases:
            task_list = case.task_list or []
            client_email = case.client_email

            client_details: dict[str, Union[str, str]] = clients_details.get(client_email, {})
            user_data = users_data.get(
                client_email, {"full_legal_name": "", "profile_pic": ""}
            )

            assignee_pps = []
            if case.assignee_list:
                for assignee in case.assignee_list:
                    if assignee and assignee in law_personnel_data:
                        assignee_pps.append(
                            law_personnel_data[assignee]["profile_picture"]
                        )

            all_cases[case.case_id] = {
                "name": case.case_name,
                "client_email": client_email,
                "client_username": self.get_immigrant(client_email).username,
                "assignees": case.assignee_list,
                "assignee_profilePics": assignee_pps,
                "task_ids": task_list,
                "status": case.case_status,
                "description": case.case_description,
                "case_type": case.case_type,
                "client_contact": client_details.get("client_number"),
                "client_address": client_details.get("client_address"),
                "client_name": user_data["full_legal_name"],
                "client_profilePic": user_data["profile_pic"],
                "intake_sent": case.case_id in intake_sent,
                "case_paid": case_paid.get(case.case_id, False),
            }

        db.close()
        return all_cases

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
    ) -> bool:
        db = self.Session()
        exist_case = (
            db.query(AllCases)
            .filter(
                AllCases.lawyer_email == lawyer_email.lower(),
                AllCases.client_email == immigrant_email.lower(),
                AllCases.case_type == case_type.lower(),
            )
            .first()
        )
        if exist_case:
            db.close()
            return True
        db.close()
        return False

    def update_connected_lawyers(
        self, immigrant_email: EmailStr, lawyer_email: EmailStr, case_id: str
    ) -> None:
        # db = self.Session()
        # connected_lawyer = (
        #     db.query(ImmigrantLawyerConnection)
        #     .filter(
        #         ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
        #         ImmigrantLawyerConnection.lawyer_email == lawyer_email.lower(),
        #         ImmigrantLawyerConnection.connected_boolean == True,
        #     )
        #     .first()
        # )
        # if connected_lawyer:
        #     if case_id not in connected_lawyer.lawyer_case_ids and case_id is not None:
        #         connected_lawyer.lawyer_case_ids.append(case_id)
        # else:
        #     connected_lawyer = ImmigrantLawyerConnection(
        #         immigrant_email=immigrant_email.lower(),
        #         lawyer_email=lawyer_email.lower(),
        #         lawyer_case_ids=[case_id],
        #         connected_boolean=True,
        #     )
        #     db.add(connected_lawyer)
        # db.commit()
        # db.close()
        # TODO: Connecte with relationshio management
        pass

    def update_clients(
        self,
        lawyer_email: EmailStr,
        client_email: EmailStr,
        client_number: str,
        client_address: str,
    ) -> None:
        # db = self.Session()
        # exist_client = (
        #     db.query(AllClients)
        #     .filter(
        #         AllClients.lawyer_email == lawyer_email.lower(),
        #         AllClients.client_email == client_email.lower(),
        #     )
        #     .first()
        # )
        # if not exist_client:
        #     self.update_lawyer_stat(lawyer_email, "client_num")
        #     new_client = AllClients(
        #         lawyer_email=lawyer_email.lower(),
        #         client_email=client_email.lower(),
        #         client_number=client_number,
        #         client_address=client_address,
        #     )
        #     db.add(new_client)
        #     db.commit()
        # else:
        #     exist_client.client_number = client_number
        #     exist_client.client_address = client_address
        #     db.commit()
        #     db.refresh(exist_client)

        # db.close()
        # TODO: connect with relationship management
        pass

    def create_case(
        self,
        lawyer_email: EmailStr,
        case_details: dict[str, EmailStr, Union[str, list[EmailStr]]],
    ) -> None:
        db = self.Session()
        self.update_clients(
            lawyer_email,
            case_details["client_email"],
            case_details["client_number"],
            case_details["client_address"],
        )
        new_case = AllCases(
            case_id=case_details["case_id"],
            lawyer_email=lawyer_email.lower(),
            client_email=case_details["client_email"].lower(),
            case_name=case_details["case_name"],
            assignee_list=[
                assignee.lower() for assignee in case_details["assignee_list"]
            ],
            case_description=case_details["description"],
            case_type=case_details["case_type"],
        )

        db.add(new_case)
        db.commit()
        db.close()

    def add_task(
        self,
        task_details: dict[str, Union[str, list[str], list[EmailStr], datetime]],
        lawyer_email: EmailStr,
    ) -> None:
        db = self.Session()
        task_documents = [
            document.replace(" ", "+") for document in task_details["document_list"]
        ]
        task_details["document_list"] = task_documents
        if "id" not in task_details:
            task_details["id"] = Encrypt.generate_uuid()

        case = (
            db.query(AllCases)
            .filter(AllCases.case_id == task_details["case_id"])
            .first()
        )
        if case:
            # print("Creating new task")
            new_task = AllTasks(
                uuid=task_details["id"],
                lawyer_email=lawyer_email.lower(),
                task_name=task_details["name"],
                task_visibility=task_details["visibility"],
                case_name=task_details["case_name"],
                case_id=task_details["case_id"],
                task_assignees=[
                    assignee.lower() for assignee in task_details["assignee_list"]
                ],
                task_status=task_details["status"],
                task_deadline=task_details["deadline"],
                task_documents=task_details["document_list"],
                task_description=task_details["description"],
            )
            # print(new_task)
            db.add(new_task)
            db.commit()
            db.refresh(new_task)
        db.close()

    def update_task(
        self,
        task_details: dict[str, Union[str, list[str], list[EmailStr], datetime]],
        lawyer_email: EmailStr,
    ) -> tuple[str, str]:
        db = self.Session()
        task = (
            db.query(AllTasks)
            .filter(
                AllTasks.lawyer_email == lawyer_email.lower(),
                AllTasks.uuid == task_details["id"],
            )
            .first()
        )
        if task:
            task.task_name = task_details["name"]
            task.task_visibility = task_details["visibility"]
            task.case_name = task_details["case_name"]
            task.case_id = task_details["case_id"]
            task.task_assignees = task_details["assignee_list"]
            task.task_status = task_details["status"]
            task.task_deadline = task_details["deadline"]
            task.task_documents = task_details["document_list"]
            task.task_description = task_details["description"]
        else:
            self.add_task(task_details, lawyer_email)
            task = (
                db.query(AllTasks)
                .filter(
                    AllTasks.lawyer_email == lawyer_email.lower(),
                    AllTasks.uuid == task_details["id"],
                )
                .first()
            )

        db.close()
        return task.task_name, task.case_id

    def add_tasks_to_case(self, task_list: list[str], case_id: str) -> None:
        db = self.Session()
        case = db.query(AllCases).filter(AllCases.case_id == case_id).first()
        if case:
            prev_tasklist = []
            if case.task_list is not None:
                prev_tasklist.extend(case.task_list)
            new_tasklist = [task for task in task_list if task not in prev_tasklist]
            prev_tasklist.extend(new_tasklist)
            case.task_list = prev_tasklist
            db.commit()
            db.refresh(case)
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
        # TODO: connect with relationship service
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
        # db = self.Session()
        # if invited_email:
        #     invitations = (
        #         db.query(Invitations)
        #         .filter(
        #             Invitations.invited_email == invited_email.lower(),
        #             Invitations.invited_type == invited_type,
        #         )
        #         .all()
        #     )
        # elif invitee_email:
        #     invitations = (
        #         db.query(Invitations)
        #         .filter(
        #             Invitations.invitee_email == invitee_email.lower(),
        #             Invitations.invited_type == invited_type,
        #         )
        #         .all()
        #     )
        # else:
        #     return HTTPException(
        #         status_code=400,
        #         detail="Either invited_email or invitee_email must be provided.",
        #     )
        # invitation_data = {
        #     "invited_client": (
        #         {
        #             invitation.invitee_email: invitation.case_type
        #             for invitation in invitations
        #         }
        #         if invitations
        #         else None
        #     ),
        #     "pending_case": (
        #         [
        #             {
        #                 "case_id": invitation.case_id,
        #                 "lawyer_email": invitation.invitee_email,
        #                 "client_email": invitation.invited_email,
        #                 "client_contact": invitation.client_number,
        #                 "client_address": invitation.client_address,
        #                 "case_name": invitation.case_name,
        #                 "case_description": invitation.case_description,
        #                 "case_type": invitation.case_type,
        #                 "assignees": invitation.assignees,
        #             }
        #             for invitation in invitations
        #         ]
        #         if invitations
        #         else None
        #     ),
        #     "pending_client": (
        #         {
        #             invitation.invited_email: {
        #                 "client_number": invitation.client_number,
        #                 "client_address": invitation.client_address,
        #                 "case_type": invitation.case_type,
        #             }
        #             for invitation in invitations
        #         }
        #         if invitations
        #         else {}
        #     ),
        #     "invited_external_lawyer": (
        #         {
        #             invitation.invitee_email: {
        #                 "client_number": invitation.client_number,
        #                 "client_address": invitation.client_address,
        #                 "case_type": invitation.case_type,
        #             }
        #             for invitation in invitations
        #         }
        #         if invitations
        #         else {}
        #     ),
        #     "invited_to_case": (
        #         {
        #             invitation.invitee_email: {
        #                 "role": invitation.member_role,
        #                 "permissions": invitation.member_permissions,
        #                 "case_id": invitation.case_id,
        #             }
        #             for invitation in invitations
        #         }
        #         if invitations
        #         else {}
        #     ),
        #     "invited_to_team": (
        #         {
        #             invitation.invitee_email: {
        #                 "role": invitation.member_role,
        #                 "permissions": invitation.member_permissions,
        #             }
        #             for invitation in invitations
        #         }
        #         if invitations
        #         else {}
        #     ),
        #     "refered_user": (
        #         [invitation.invitee_email for invitation in invitations][0]
        #         if invitations
        #         else None
        #     ),
        # }
        # result = invitation_data[invited_type]
        # if result == []:
        #     result = None
        # db.close()
        # return result
        # TODO: connect with relationship service
        pass

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
        # db = self.Session()
        # inviteee_email = invitee_email.lower() if invitee_email else None
        # invitation_data = {
        #     "invited_client": db.query(Invitations)
        #     .filter(
        #         Invitations.invited_email == invited_email.lower(),
        #         Invitations.invited_type == invited_type,
        #     )
        #     .first(),
        #     "pending_case": db.query(Invitations)
        #     .filter(
        #         Invitations.invited_type == invited_type, Invitations.case_id == case_id
        #     )
        #     .first(),
        #     "pending_client": db.query(Invitations)
        #     .filter(
        #         Invitations.invited_type == invited_type,
        #         Invitations.invited_email == invited_email.lower(),
        #         Invitations.invitee_email == inviteee_email,
        #     )
        #     .first(),
        #     "invited_external_lawyer": db.query(Invitations)
        #     .filter(
        #         Invitations.invited_type == invited_type,
        #         Invitations.invited_email == invited_email.lower(),
        #         Invitations.invitee_email == inviteee_email,
        #     )
        #     .first(),
        #     "invited_to_case": db.query(Invitations)
        #     .filter(
        #         Invitations.invited_type == invited_type,
        #         Invitations.invited_email == invited_email.lower(),
        #         Invitations.invitee_email == inviteee_email,
        #         Invitations.case_id == case_id,
        #     )
        #     .first(),
        #     "invited_to_team": db.query(Invitations)
        #     .filter(
        #         Invitations.invited_type == invited_type,
        #         Invitations.invited_email == invited_email.lower(),
        #         Invitations.invitee_email == inviteee_email,
        #     )
        #     .first(),
        #     "refered_user": db.query(Invitations)
        #     .filter(
        #         Invitations.invited_email == invited_email.lower(),
        #         Invitations.invited_type == invited_type,
        #     )
        #     .first(),
        # }
        # invitation = invitation_data[invited_type]
        # if invitation:
        #     db.delete(invitation)
        #     db.commit()
        # db.close()
        # TODO: connect with relationship service
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

    def remove_recommended_lawpersonnel(self, immigrant_email, lawpersonnel_email) -> bool:
        # TODO: connect with ai agent module
        pass

    def get_closed_cases(
        self, lawyer_email: EmailStr
    ) -> dict[str, dict[str, Union[str, list[EmailStr], list[str], datetime]]]:
        db = self.Session()
        all_cases = {}
        cases = (
            db.query(AllCases)
            .filter(
                AllCases.lawyer_email == lawyer_email.lower(),
                AllCases.case_status == "Closed",
            )
            .all()
        )
        if cases:
            for case in cases:
                all_cases[case.case_id] = {
                    "name": case.case_name,
                    "client_email": case.client_email,
                    "assignees": case.assignee_list,
                    "tasks": case.task_list if case.task_list is not None else [],
                    "status": case.case_status,
                    "description": case.case_description,
                }
        db.close()
        return all_cases

    def add_recent_action(
        self, lawyer_email: EmailStr, case_id: str, action: str, actor: str, role: str
    ) -> None:
        db = self.Session()
        action_time = datetime.now(timezone.utc)
        new_action = CaseRecentActions(
            lawyer_email=lawyer_email.lower(),
            lawyer_case=case_id,
            action=action,
            actor=actor,
            role=role,
            action_time=action_time,
        )

        db.add(new_action)
        db.commit()
        db.close()

    def retrieve_recent_actions(
        self, lawyer_email: EmailStr, case_id: str
    ) -> dict[str, dict[str, str]]:
        db = self.Session()
        case_actions = (
            db.query(CaseRecentActions)
            .filter(
                CaseRecentActions.lawyer_email == lawyer_email.lower(),
                CaseRecentActions.lawyer_case == case_id,
            )
            .all()
        )
        results = {}
        if case_actions:
            for case_action in case_actions:
                results[str(case_action.action_time)] = {
                    "action": case_action.action,
                    "actor": case_action.actor,
                    "role": case_action.role,
                }

        db.close()
        return results

    def retrieve_lawyer_case_sub(
        self, case_id: str
    ) -> dict[str, Union[EmailStr, str, bool]]:
        # db = self.Session()
        # case_sub = (
        #     db.query(LawyerCaseSubs).filter(LawyerCaseSubs.case_id == case_id).first()
        # )
        # if case_sub:
        #     db.close()
        #     return case_sub.to_dict()
        # db.close()
        # return {}
        # TODO: connect with billing module
        pass

    def modify_lawyer_case_sub(
        self, case_id: str, to_cancel: bool
    ) -> bool:
        cancel_string = "restart"
        if to_cancel:
            cancel_string = "cancel"
        # TODO: connect with billing module
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

    def retrieve_specific_case(
        self, lawyer_email: EmailStr, case_id: str
    ) -> tuple[list[EmailStr], EmailStr]:
        db = self.Session()
        case = (
            db.query(AllCases)
            .filter(
                AllCases.lawyer_email == lawyer_email.lower(),
                AllCases.case_id == case_id,
            )
            .first()
        )
        assignees = []
        client_email = None
        if case:
            assignees = case.assignee_list if case.assignee_list is not None else []
            client_email = case.client_email

        db.close()
        return assignees, client_email

    def update_case(
        self,
        lawyer_email: EmailStr,
        case_id: str,
        case_name: str,
        case_description: str,
    ) -> int:
        db = self.Session()
        case = (
            db.query(AllCases)
            .filter(
                AllCases.lawyer_email == lawyer_email.lower(),
                AllCases.case_id == case_id,
            )
            .first()
        )
        success = 0
        if case:
            case.case_name = case_name
            case.case_description = case_description
            db.commit()
            db.refresh(case)
            success = 1
        db.close()
        return success

    def retrieve_client_cases(
        self, lawyer_email: EmailStr, client_email: EmailStr
    ) -> list[dict[str, str]]:
        db = self.Session()
        all_cases = []
        cases = (
            db.query(AllCases)
            .filter(
                AllCases.lawyer_email == lawyer_email.lower(),
                AllCases.client_email == client_email.lower(),
                AllCases.case_status != "Closed",
            )
            .all()
        )
        if cases:
            for case in cases:
                all_cases.append(
                    {
                        "id": case.case_id,
                        "name": case.case_name,
                        "description": case.case_description,
                    }
                )
        db.close()
        return all_cases

    def delete_case(self, lawpersonnel_email: EmailStr, case_id: str):
        # TODO: connect with user service (Cleanup)
        pass

    def get_all_tasks(
        self, lawyer_email: EmailStr
    ) -> list[dict[str, Union[str, list[str], list[EmailStr], datetime]]]:
        db = self.Session()
        all_tasks = []
        tasks = (
            db.query(AllTasks)
            .filter(AllTasks.lawyer_email == lawyer_email.lower())
            .all()
        )
        if tasks:
            for task in tasks:
                all_tasks.append(
                    {
                        "id": task.uuid,
                        "name": task.task_name,
                        "visibility": task.task_visibility,
                        "case_name": task.case_name,
                        "case_id": task.case_id,
                        "assignee_list": task.task_assignees,
                        "status": task.task_status,
                        "deadline": task.task_deadline,
                        "document_list": task.task_documents,
                        "description": task.task_description,
                    }
                )
        db.close()
        return all_tasks

    def add_case_document(
        self,
        lawyer_email: EmailStr,
        case_id: str,
        document_url: str,
        filename: str,
        folder_name: str,
    ) -> tuple[str, str, str]:
        # doc_url = document_url.replace(" ", "+")
        # db = self.Session()
        # file_id = generate_uuid()
        # exist_document = (
        #     db.query(CaseDocuments)
        #     .filter(
        #         CaseDocuments.lawyer_email == lawyer_email.lower(),
        #         CaseDocuments.lawyer_case == case_id,
        #         CaseDocuments.document_url == doc_url.lower(),
        #     )
        #     .all()
        # )
        # if not exist_document and (
        #     self.check_if_paid(case_id)
        #     or self.get_lawpersonnel(lawyer_email).username
        #     in ["codyfisher", "dlane", "drobertson", "ghawkins", "carter.elizabeth1965"]
        # ):
        #     new_document = CaseDocuments(
        #         uuid=file_id,
        #         filename=filename,
        #         document_url=doc_url,
        #         folder_name=folder_name,
        #         lawyer_email=lawyer_email.lower(),
        #         lawyer_case=case_id,
        #     )
        #     db.add(new_document)
        #     db.commit()
        # db.close()
        # return filename, doc_url, file_id
        # TODO: Connect with documents module
        pass

    def retrieve_task(
        self, lawyer_email: EmailStr, task_id: str
    ) -> dict[str, Union[str, list[str], list[EmailStr], datetime]]:
        db = self.Session()
        task = (
            db.query(AllTasks)
            .filter(
                AllTasks.lawyer_email == lawyer_email.lower(),
                AllTasks.uuid == task_id,
                AllTasks.task_status != "Rejected",
            )
            .first()
        )
        result = {}
        if task:
            result["id"] = task.uuid
            result["name"] = task.task_name
            result["visibility"] = task.task_visibility
            result["case_name"] = task.case_name
            result["case_id"] = task.case_id
            result["assignee_list"] = task.task_assignees
            result["status"] = task.task_status
            result["deadline"] = task.task_deadline
            result["document_list"] = task.task_documents
            result["description"] = task.task_description

        db.close()
        return result

    def retrieve_case_specific_tasks(
        self, lawyer_email: EmailStr, case_id: str
    ) -> list[dict[str, Union[str, list[str], list[EmailStr], datetime]]]:
        db = self.Session()
        all_tasks = []
        today = datetime.now(timezone.utc).date()

        case = (
            db.query(AllCases)
            .filter(
                AllCases.lawyer_email == lawyer_email.lower(),
                AllCases.case_id == case_id,
            )
            .first()
        )

        if case and case.task_list is not None:
            for task_id in case.task_list:
                task = self.retrieve_task(lawyer_email, task_id)
                if task:
                    all_tasks.append(task)

        completed_tasks = [task for task in all_tasks if task.get("status") == "Done"]
        pending_tasks = [task for task in all_tasks if task.get("status") != "Done"]

        for task in pending_tasks:
            if task.get("deadline") and isinstance(task.get("deadline"), str):
                task["deadline_date"] = datetime.strptime(
                    task["deadline"], "%Y-%m-%d"
                ).date()
            else:
                task["deadline_date"] = datetime.max.date()

        for task in completed_tasks:
            if task.get("task_completed_date") and isinstance(
                task.get("task_completed_date"), str
            ):
                task["completed_date"] = datetime.strptime(
                    task["task_completed_date"], "%Y-%m-%d"
                ).date()
            if task.get("deadline") and isinstance(task.get("deadline"), str):
                task["completed_date"] = datetime.strptime(
                    task["deadline"], "%Y-%m-%d"
                ).date()
            else:
                task["completed_date"] = datetime.max.date()

        pending_tasks.sort(key=lambda x: (x.get("deadline_date") - today).days)
        completed_tasks.sort(key=lambda x: (x.get("completed_date") - today).days)
        sorted_tasks = pending_tasks + completed_tasks
        for task in sorted_tasks:
            if "deadline_date" in task:
                del task["deadline_date"]
            if "completed_date" in task:
                del task["completed_date"]
        db.close()
        return sorted_tasks

    def add_case_teammate(
        self,
        lawyer_email: EmailStr,
        case_id: str,
        member_name: str,
        member_email: EmailStr,
    ) -> None:
        db = self.Session()
        lawyer = self.get_lawpersonnel(lawyer_email)
        role = lawyer.personnel_type.capitalize()
        action = f"has added {member_name} to the case"
        actor = f"{lawyer.full_legal_name}"
        self.add_recent_action(lawyer_email, case_id, action, actor, role)
        self.update_lawyer_stat(lawyer_email, "assignee_num")
        team_member = (
            db.query(LawyerTeams)
            .filter(
                LawyerTeams.lawyer_email == lawyer_email.lower(),
                LawyerTeams.member_email == member_email.lower(),
            )
            .first()
        )
        if team_member:
            cases = team_member.lawyer_cases
            if not cases:
                cases = []
            if case_id not in cases:
                cases.append(case_id)
            team_member.lawyer_cases = cases
            db.commit()
            db.refresh(team_member)
        else:
            member = self.get_lawpersonnel(member_email)
            member_role = "Lawyer"
            if member:
                member_role = member.personnel_type.capitalize()
            self.add_team_member(
                lawyer_email=lawyer_email,
                member_email=member_email,
                member_role=member_role,
                member_permissions="Viewer",
            )
            team_member = (
                db.query(LawyerTeams)
                .filter(
                    LawyerTeams.lawyer_email == lawyer_email.lower(),
                    LawyerTeams.member_email == member_email.lower(),
                )
                .first()
            )

        case_team = self.get_case_team(lawyer_email, case_id)
        if member_email not in case_team:
            new_member = CaseTeams(
                lawyer_email=lawyer_email.lower(),
                lawyer_case=case_id,
                member_name=member_name,
                member_type=team_member.member_role,
                member_email=member_email.lower(),
            )
            case_team[member_email] = {
                "member_type": team_member.member_role,
                "name": member_name,
            }
            db.add(new_member)
            db.commit()

        lawyer_case = (
            db.query(AllCases)
            .filter(
                AllCases.lawyer_email == lawyer_email.lower(),
                AllCases.case_id == case_id,
            )
            .first()
        )
        if lawyer_case:
            assignees = [assignee.lower() for assignee in lawyer_case.assignee_list]
            for member in case_team:
                if member.lower() not in assignees:
                    assignees.append(member.lower())
            lawyer_case.assignee_list = assignees
            db.commit()
            db.refresh(lawyer_case)

        db.close()

    def add_team_member(
        self,
        lawyer_email: EmailStr,
        member_email: EmailStr,
        member_role: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"],
        member_permissions: Literal["Admin", "Commenter", "Viewer"],
    ) -> None:
        db = self.Session()
        exist_team_member = (
            db.query(LawyerTeams)
            .filter(
                LawyerTeams.lawyer_email == lawyer_email.lower(),
                LawyerTeams.member_email == member_email.lower(),
            )
            .first()
        )
        if not exist_team_member:
            new_team_member = LawyerTeams(
                member_role=member_role,
                member_email=member_email.lower(),
                lawyer_email=lawyer_email.lower(),
                member_permissions=member_permissions,
            )
            db.add(new_team_member)
            db.commit()
        db.close()

    def retrieve_team_members(
        self, lawyer_email: EmailStr
    ) -> dict[EmailStr, dict[str, Union[str, list[str]]]]:
        db = self.Session()
        team_members = (
            db.query(LawyerTeams)
            .filter(LawyerTeams.lawyer_email == lawyer_email.lower())
            .all()
        )
        results = {}
        if team_members:
            for team_member in team_members:
                results[team_member.member_email] = {
                    "role": team_member.member_role,
                    "permissions": team_member.member_permissions,
                    "cases": team_member.lawyer_cases,
                }
        db.close()
        return results

    def edit_team_members(
        self,
        lawyer_email: EmailStr,
        member_email: EmailStr,
        new_permissions: Literal["Admin", "Commenter", "Viewer"] = None,
    ) -> None:
        db = self.Session()
        team_member = (
            db.query(LawyerTeams)
            .filter(
                LawyerTeams.lawyer_email == lawyer_email.lower(),
                LawyerTeams.member_email == member_email.lower(),
            )
            .first()
        )
        if team_member:
            if (
                new_permissions is not None
                and team_member.member_permissions != new_permissions
            ):
                team_member.member_permissions = new_permissions
            db.commit()
            db.refresh(team_member)
        db.close()

    def get_case_team(
        self, lawyer_email: EmailStr, case_id: str
    ) -> dict[EmailStr, dict[str, str]]:
        db = self.Session()
        case_members = (
            db.query(CaseTeams)
            .filter(
                CaseTeams.lawyer_email == lawyer_email.lower(),
                CaseTeams.lawyer_case == case_id,
            )
            .all()
        )
        results = {}
        if case_members:
            for case_member in case_members:
                results[case_member.member_email] = {
                    "member_type": case_member.member_type,
                    "name": case_member.member_name,
                }

        db.close()
        return results

    def remove_case_member(
        self, lawyer_email: EmailStr, case_id: str, member_email: EmailStr
    ) -> None:
        db = self.Session()
        case_member = (
            db.query(CaseTeams)
            .filter(
                CaseTeams.lawyer_email == lawyer_email.lower(),
                CaseTeams.lawyer_case == case_id,
                CaseTeams.member_email == member_email.lower(),
            )
            .first()
        )
        if case_member:
            db.delete(case_member)

        case = (
            db.query(AllCases)
            .filter(
                AllCases.lawyer_email == lawyer_email.lower(),
                AllCases.case_id == case_id,
            )
            .first()
        )
        if case:
            assignee_list = [
                assignee
                for assignee in case.assignee_list
                if assignee != member_email.lower()
            ]
            case.assignee_list = assignee_list

        db.commit()
        db.refresh(case)
        db.close()

    def retrieve_case_types(self) -> dict[str, dict[str, Union[str, list[dict[str, Union[str, int]]], dict[str, dict[str, Union[str, list[dict[str, Union[str, int]]]]]]]]]:
        case_types = {}
        with open("./data/case_types.json", "r") as fp:
            case_types = json.load(fp)
        return case_types

    def update_task_status(
        self,
        lawyer_email: EmailStr,
        task_id: str,
        status: str = Literal["To-Do", "In-Progress", "In-Review", "Done", "Rejected"],
    ) -> tuple[int, str, str]:
        db = self.Session()
        task = (
            db.query(AllTasks)
            .filter(
                AllTasks.lawyer_email == lawyer_email.lower(), AllTasks.uuid == task_id
            )
            .first()
        )
        success = 0
        task_name = None
        case_id = None
        if task:
            task.task_status = status
            if status == "Done":
                task.task_completed_date = datetime.now(timezone.utc).date().isoformat()
            success = 1
            task_name = task.task_name
            case_id = task.case_id
            db.commit()
            db.refresh(task)

        db.close()
        return success, task_name, case_id

    def retrieve_case_name(self, lawyer_email: EmailStr, case_id: str) -> str:
        db = self.Session()
        case_name = None
        case = (
            db.query(AllCases)
            .filter(
                AllCases.lawyer_email == lawyer_email.lower(),
                AllCases.case_id == case_id,
            )
            .first()
        )
        if case:
            case_name = case.case_name
        db.close()
        return case_name
