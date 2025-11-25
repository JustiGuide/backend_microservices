from __future__ import annotations
import json
import re
from typing import Annotated
from fastapi import Form, HTTPException
import phonenumbers
from pydantic import AfterValidator, BaseModel, EmailStr, Field, HttpUrl, ValidationError, model_validator
import os
from dotenv import load_dotenv
from database import AllTasks, CaseTeams, Connection, AllCases, LawPersonnel, LawyerTeams
import datetime

load_dotenv()


class TaskDetailsValidator(BaseModel):
    username: str
    task_id: str
    docs_to_delete: list[HttpUrl] = None
    assignees_to_remove: list[EmailStr] = None
    case_id: str
    assignees_to_add: list[EmailStr] = None
    task_name: str = None
    visibility: TaskVisibility = None
    status: TaskStatus = None
    deadline: DateString = None
    description: str = None

    @model_validator(mode="after")
    def validate_all_task_details(self) -> TaskDetailsValidator:
        Authorizer.taskid_validator(self.task_id, self.username)
        Authorizer.lawyer_case_validator(self.case_id, self.username)
        if self.docs_to_delete is not None:
            Authorizer.validate_task_documents(self.task_id, self.docs_to_delete)
        if self.assignees_to_remove is not None:
            Authorizer.validate_task_assignees(self.task_id, self.assignees_to_remove)
        if self.assignees_to_add is not None:
            Authorizer.validate_case_members(self.case_id, self.assignees_to_add)
        return self


class Authorizer:
    SECRET_KEY = os.getenv("OAUTH_KEY")
    AUTH_BYPASS = bool(int(os.getenv("AUTH_BYPASS")))
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 15
    Session = Connection().SessionLocal

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
    def client_email_validator(
        client_email: EmailStr, lawpersonnel_email: EmailStr
    ) -> EmailStr:
        # TODO: Connect with relationship management service
        return client_email

    @staticmethod
    def casetype_validator(casetype: str) -> str:
        valid_casetypes = [
            "nonimmigrant_worker",
            "employment_auth",
            "alien_rel",
            "asylum_removal",
            "naturalization",
        ]
        if casetype not in valid_casetypes:
            raise HTTPException(
                status_code=405,
                detail=f"Invalid case type. Must be one of {valid_casetypes}.",
            )
        return casetype

    @staticmethod
    def lawyer_team_validator(
        lawpersonnel_email: EmailStr = Form(...), assignees: list[EmailStr] = Form(...)
    ) -> list[EmailStr]:
        db = Authorizer.Session()
        all_members = db.query(LawyerTeams.member_email, LawyerTeams.lawyer_email).all()
        if not all_members:
            db.close()
            raise HTTPException(status_code=405, detail="No members found.")
        if not all(
            member
            in [member[0] for member in all_members if member[1] == lawpersonnel_email]
            for member in assignees
        ):
            db.close()
            raise HTTPException(status_code=405, detail="Invalid members.")
        db.close()
        return assignees
    @staticmethod
    def lawyer_case_validator(case_id: str, lawyer_email: EmailStr) -> str:
        db = Authorizer.Session()
        all_cases = db.query(AllCases.case_id, AllCases.lawyer_email).all()
        if case_id not in [case[0] for case in all_cases if case[1] == lawyer_email]:
            db.close()
            raise HTTPException(status_code=405, detail="Case ID is not connected to the lawyer.")
        db.close()
        return case_id

    @staticmethod
    def casestatus_validator(status: str) -> str:
        valid_casestatuses = ["In Progress", "Submitted", "Closed"]
        if status not in valid_casestatuses:
            raise HTTPException(status_code=405, detail=f"Invalid case status. Must be one of {valid_casestatuses}.")
        return status

    def validate_task_documents(
        task_id: str, docs_to_delete: list[HttpUrl] = []
    ) -> list[HttpUrl]:
        db = Authorizer.Session()
        all_docs = db.query(AllTasks.task_documents, AllTasks.uuid).all()
        if not all_docs:
            db.close()
            raise HTTPException(status_code=405, detail="No documents found.")
        if not all(
            doc in [doc[0] for doc in all_docs if doc[1] == task_id]
            for doc in docs_to_delete
        ):
            db.close()
            raise HTTPException(status_code=405, detail="Invalid documents.")
        db.close()
        return docs_to_delete

    def validate_task_assignees(
        task_id: str, assignees_to_remove: list[EmailStr] = []
    ) -> list[EmailStr]:
        db = Authorizer.Session()
        all_assignees = db.query(AllTasks.task_assignees, AllTasks.uuid).all()
        if not all_assignees:
            db.close()
            raise HTTPException(status_code=405, detail="No assignees found.")
        if not all(
            assignee
            in [assignee[0] for assignee in all_assignees if assignee[1] == task_id]
            for assignee in assignees_to_remove
        ):
            db.close()
            raise HTTPException(status_code=405, detail="Invalid assignees.")
        db.close()
        return assignees_to_remove

    def validate_case_members(
        case_id: str, assignees_to_add: list[EmailStr] = []
    ) -> list[EmailStr]:
        db = Authorizer.Session()
        all_members = db.query(CaseTeams.member_email, CaseTeams.lawyer_case).all()
        if not all_members:
            db.close()
            raise HTTPException(status_code=405, detail="No members found.")
        if not all(
            member in [member[0] for member in all_members if member[1] == case_id]
            for member in assignees_to_add
        ):
            db.close()
            raise HTTPException(status_code=405, detail="Invalid members.")
        db.close()
        return assignees_to_add

    @staticmethod    
    def task_visibility_validator(taskvisibility: str) -> str:
        valid_taskvisibilities = ["all", "assigned"]
        if taskvisibility not in valid_taskvisibilities:
            raise HTTPException(status_code=405, detail=
                f"Invalid task visibility. Must be one of {valid_taskvisibilities}."
            )
        return taskvisibility

    @staticmethod
    def validate_case_id_email(
        email_id: EmailStr = Form(...), case_id: str = Form(...)
    ) -> str:
        db = Authorizer.Session()
        all_cases = db.query(AllCases.case_id, AllCases.lawyer_email).all()
        if case_id not in [case[0] for case in all_cases if case[1] == email_id]:
            db.close()
            raise HTTPException(
                status_code=405, detail="Case ID is not connected to the user."
            )
        db.close()
        return case_id

    @staticmethod
    def validate_case_name(case_id: str = Form(...), case_name: str = Form(...)) -> str:
        db = Authorizer.Session()
        all_cases = db.query(AllCases.case_id, AllCases.case_name).all()
        if case_name not in [case[1] for case in all_cases if case[0] == case_id]:
            db.close()
            raise HTTPException(status_code=405, detail="Case name is not connected to the case ID.")
        db.close()
        return case_name

    @staticmethod
    def taskstatus_validator(taskstatus: str) -> str:
        valid_taskstatuses = ["To-Do", "In-Progress", "In-Review", "Done", "Rejected"]
        if taskstatus not in valid_taskstatuses:
            raise HTTPException(
                status_code=405,
                detail=f"Invalid task status. Must be one of {valid_taskstatuses}.",
            )
        return taskstatus

    @staticmethod
    def validate_date(date_str: str) -> datetime.date:
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d").date().isoformat()
        except ValueError:
            raise HTTPException(
                status_code=405, detail="Invalid date format. Use YYYY-MM-DD."
            )

    @staticmethod
    def taskid_validator(task_id: str = Form(...), lawpersonnel_username: str = Form(...)) -> str:
        db = Authorizer.Session()
        lawyer = (
            db.query(LawPersonnel)
            .filter(LawPersonnel.username == lawpersonnel_username)
            .first()
        )
        if not lawyer:
            db.close()
            raise HTTPException(status_code=405, detail="Lawyer not found.")
        all_tasks = db.query(AllTasks.uuid, AllTasks.lawyer_email).all()
        if task_id not in [task[0] for task in all_tasks if task[1] == lawyer.email]:
            db.close()
            raise HTTPException(status_code=405, detail="Invalid task ID for the lawyer.")
        db.close()
        return task_id

    @staticmethod
    def task_details_validator(task_json: str) -> TaskDetailsValidator:
        try:
            task_details = json.loads(task_json)
            if not isinstance(task_details, dict):
                raise HTTPException(
                    status_code=405, detail="Task details must be a dictionary."
                )
            return TaskDetailsValidator(**task_details)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=405, detail="Invalid JSON format for task details."
            )
        except ValidationError as e:
            raise HTTPException(status_code=405, detail=f"Validation error: {e}")

    @staticmethod
    def permissions_validator(permissions: str) -> str:
        valid_permissions = ["Admin", "Editor", "Viewer"]
        if permissions not in valid_permissions:
            raise HTTPException(status_code=405, detail=f"Invalid permission. Must be one of {valid_permissions}.")
        return permissions

    @staticmethod
    def casemember_validator(case_id: str, member_email: EmailStr) -> EmailStr:
        db = Authorizer.Session()
        all_members = db.query(CaseTeams.member_email, CaseTeams.lawyer_case).all()
        if member_email not in [
            member[0] for member in all_members if member[1] == case_id
        ]:
            db.close()
            raise HTTPException(status_code=405, detail="User is not a member of the case.")
        db.close()
        return member_email


PhoneNumber = Annotated[
    str,
    Field(description="A contact phone number, ideally in E.164 format."),
    AfterValidator(Authorizer.phonenumber_validator),
]

CaseType = Annotated[
    str, Field(description="Case type."), AfterValidator(Authorizer.casetype_validator)
]

LawyerCaseID = Annotated[
    str,
    Field(description="Lawyer's case ID"),
    AfterValidator(Authorizer.lawyer_case_validator),
]

CaseStatus = Annotated[
    str,
    Field(description="Case status."),
    AfterValidator(Authorizer.casestatus_validator),
]

TaskVisibility = Annotated[
    str,
    Field(description="Task visibility."),
    AfterValidator(Authorizer.task_visibility_validator),
]

TaskStatus = Annotated[
    str, Field(description="Task status."), AfterValidator(Authorizer.taskstatus_validator)
]

DateString = Annotated[
    str,
    Field(
        description="A date string in YYYY-MM-DD format.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    AfterValidator(Authorizer.validate_date),
]

TaskDetails = Annotated[
    str,
    Field(description="Task details in JSON format."),
    AfterValidator(Authorizer.task_details_validator),
]

MemberPermissions = Annotated[
    str, Field(description="Member Permissions."), AfterValidator(Authorizer.permissions_validator)
]

MemberEmail = Annotated[
    str,
    Field(description="Member Email ID"),
    AfterValidator(Authorizer.casemember_validator),
]
