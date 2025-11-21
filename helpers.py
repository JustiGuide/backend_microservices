from datetime import datetime, timedelta, timezone
import string
import re
from typing import Any, Literal, Union
from fastapi import UploadFile
from pydantic import BaseModel, EmailStr
from database import Immigrants, LawPersonnel, Functions
from email_gateway import Email

db_func = Functions()

class UploadFile_Dummy(BaseModel):
    size: int
    content_type: str


class Helpers:
    @staticmethod
    def add_notification(receiver: EmailStr, sender: EmailStr, type: Literal["cases", "tasks", "connection", "kyc", "forms", "teams", "lawyer_chat", "intake", "case_payment"], content: str, target_id: dict[str, Any], one_time:bool=False, created_at:datetime=None):
        # TODO: connect with user management service
        # db = db_func.Session()
        # if created_at is None:
        #     notification_alert = NotificationAlerts(
        #         receiver = receiver.lower(),
        #         sender = sender.lower(),
        #         type = type,
        #         content = content,
        #         target_id = target_id,
        #         one_time = one_time
        #     )
        #     db.add(notification_alert)

        # if type == "kyc":
        #     notification_alert = db.query(NotificationAlerts).filter(NotificationAlerts.receiver == receiver.lower(), NotificationAlerts.type == type, NotificationAlerts.target_id == target_id).first()
        #     if notification_alert:
        #         notification_alert.update_created_at()
        #         db.commit()
        # else:
        #     notification_alert = NotificationAlerts(
        #         receiver = receiver.lower(),
        #         sender = sender.lower(),
        #         type = type,
        #         content = content,
        #         target_id = target_id,
        #         one_time = one_time,
        #         created_at = created_at
        #     )
        #     db.add(notification_alert)

        # db.commit()
        pass

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
        # db = db_func.Session()
        # notifications = (
        #     db.query(NotificationAlerts)
        #     .filter(
        #         NotificationAlerts.receiver == email.lower(),
        #         NotificationAlerts.type == type,
        #     )
        #     .all()
        # )
        # if notifications:
        #     for notification in notifications:
        #         if id is not None:
        #             if notification.id == id:
        #                 db.delete(notification)
        #                 db.commit()
        #             return "Deleted specific notification"
        #         elif data is not None:
        #             if notification.target_id == data:
        #                 db.delete(notification)
        #                 db.commit()
        #             return "Deleted specific notification"
        #         elif content is not None:
        #             if notification.content == content:
        #                 db.delete(notification)
        #                 db.commit()
        #         else:
        #             return "Cannot delete specific notification"
        # else:
        #     return f"No notifications found for this user of type {type}"
        # TODO: connect with user management service
        pass

    @staticmethod
    def calculate_deadline(num_days: int) -> tuple[str, datetime, datetime]:
        today = datetime.now(timezone.utc)
        days_added = 0
        current_date = today
        while days_added < num_days:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:
                days_added += 1

        deadline_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        deadline_prev = deadline_date - timedelta(days=1)
        deadline_curr = deadline_date.replace(
            hour=23, minute=59, second=59, microsecond=0
        )

        return current_date.strftime("%Y-%m-%d"), deadline_prev, deadline_curr

    @staticmethod
    def calculate_updated_deadline(
        new_deadline: str
    ) -> tuple[datetime, datetime, datetime]:
        deadline = datetime.strptime(new_deadline, "%Y-%m-%d")
        deadline = deadline.astimezone(tz=timezone.utc)
        deadline_date = deadline.replace(hour=0, minute=0, second=0, microsecond=0)
        deadline_prev = deadline_date - timedelta(days=1)
        deadline_curr = deadline_date.replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        return deadline, deadline_prev, deadline_curr

    @staticmethod
    def get_case_name(
        case_type: str
    ) -> str:
        all_case_types = Helpers.get_all_casetypes()
        return all_case_types[case_type]["case"]

    @staticmethod
    def get_all_casetypes() -> (
        dict[str, dict[str, Union[str, list[dict[str, Union[str, int]]]]]]
    ):
        # TODO: Connect with case management service to get case type based on form_name (case_type.json)
        pass

    @staticmethod
    def send_task_deadline(
        lawyer: LawPersonnel,
        task_details: dict,
        deadline_type: str,
    ):
        Email.send_deadline_alert(lawyer, task_details, deadline_type)

    @staticmethod
    def remove_invitation(
        invL_bool: bool,
        pendCl_bool: bool,
        invEL_bool: bool,
        lawyer: LawPersonnel,
        client: Immigrants,
        case_id: str,
    ) -> None:
        try:
            if invEL_bool:
                Helpers.add_notification(
                    client.email,
                    lawyer.email,
                    "connection",
                    f"{lawyer.full_legal_name} has joined the platform and connected with you",
                    {"lawyer_email": lawyer.email},
                )
                db_func.delete_invitation_data(
                    invited_type="invited_external_lawyer",
                    invited_email=lawyer.email,
                    invitee_email=client.email,
                )
                db_func.remove_external_lawyer(email=lawyer.email)
            elif pendCl_bool:
                Helpers.add_notification(
                    client.email,
                    lawyer.email,
                    "connection",
                    f"{lawyer.full_legal_name} has accepted your connection request and started a case with you",
                    {"lawyer_email": lawyer.email},
                )
                db_func.delete_invitation_data(
                    invited_type="pending_client",
                    invited_email=lawyer.email,
                    invitee_email=client.email,
                )
            elif invL_bool:
                db_func.delete_invitation_data(
                    invited_type="invited_client", invited_email=client.email
                )
            db_func.delete_invitation_data(invited_type="pending_case", case_id=case_id)
            db_func.remove_recommended_lawpersonnel(
                client_email=client.email, lawyer_email=lawyer.email
            )
        except Exception as exc:
            print("Background task failed")

    def store_file(
        file: Union[UploadFile, UploadFile_Dummy],
        file_url: str,
        email_id: EmailStr,
        filename: str,
        readable: bool = False,
    ) -> str:
        # TODO: Connect with docs Service
        # def get_file_size(file_size: int) -> str:
        #     if file_size < 1024:
        #         return f"{file_size} B"
        #     elif file_size < 1024**2:
        #         return f"{file_size / 1024:.2f} KB"
        #     elif file_size < 1024**3:
        #         return f"{file_size / 1024**2:.2f} MB"
        #     else:
        #         return f"{file_size / 1024**3:.2f} GB"

        # def add_file(
        #     self,
        #     file_name: str,
        #     file_size: str,
        #     file_url: str,
        #     file_type: str,
        #     readable: bool,
        #     email_id: EmailStr,
        # ) -> str:
        #     db = self.Session()
        #     user = self.get_immigrant(email_id)
        #     lawyer = self.get_lawpersonnel(email_id)
        #     if user:
        #         owner = email_id
        #         owner_type = "user"
        #     elif lawyer:
        #         owner = email_id
        #         owner_type = lawyer.personnel_type
        #     else:
        #         return HTTPException(
        #             status_code=400,
        #             detail="User or Lawyer not found",
        #         )

        #     file_id = None
        #     exist_file = (
        #         db.query(AllFiles)
        #         .filter(AllFiles.file_url == file_url, AllFiles.owner == owner)
        #         .first()
        #     )
        #     if not exist_file:
        #         new_file = AllFiles(
        #             file_name=file_name,
        #             file_size=file_size,
        #             file_url=file_url,
        #             file_type=file_type,
        #             open_read=readable,
        #             owner=owner,
        #             owner_type=owner_type,
        #         )
        #         db.add(new_file)
        #         db.commit()
        #         db.refresh(new_file)
        #         file_id = new_file.uuid
        #     else:
        #         exist_file.file_name = file_name
        #         exist_file.file_size = file_size
        #         exist_file.file_type = file_type
        #         exist_file.owner_type = owner_type
        #         exist_file.open_read = readable
        #         file_id = exist_file.uuid
        #         db.commit()
        #     db.close()
        #     return file_id

        # file_id = db_func.add_file(
        #     file_name=filename,
        #     file_size=get_file_size(file.size),
        #     file_url=file_url,
        #     file_type=file.content_type,
        #     readable=readable,
        #     email_id=email_id,
        # )
        # return file_id
        return ""

    @staticmethod
    def get_legal_filename(filename: str) -> str:
        legal_chars = set(string.ascii_letters + string.digits + "._-")
        cleaned_filename = "".join(c for c in filename if c in legal_chars)
        cleaned_filename = re.sub(r"\.+", ".", cleaned_filename)
        cleaned_filename = cleaned_filename.strip(". ")
        if not cleaned_filename:
            cleaned_filename = "file"
        max_length = 255
        if len(cleaned_filename) > max_length:
            cleaned_filename = cleaned_filename[:max_length]
        return cleaned_filename
