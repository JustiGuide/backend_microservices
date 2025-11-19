from datetime import datetime
import mimetypes
import os
import string
import re
from typing import Any, Literal, Union
from fastapi import UploadFile
from pydantic import BaseModel, EmailStr
import requests
from database import Functions

db_func = Functions()


class UploadFile_Dummy(BaseModel):
    size: int
    content_type: str


class Helpers:

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

    @staticmethod
    def retrieve_connected_lawyers(
        immigrant_email: EmailStr, case_id: str = None, only_emails: bool = False
    ) -> list[dict[str, Union[str, bool, list[str]]]]:
        # TODO: Connect with relationship microservice
        # db = self.Session()
        # lawyers = []
        # connected_lawyers = (
        #     db.query(ImmigrantLawyerConnection)
        #     .filter(
        #         ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
        #         ImmigrantLawyerConnection.connected_boolean == True,
        #     )
        #     .all()
        # )
        # if connected_lawyers:
        #     # print(f"Connected lawyers for {immigrant_email}: {len(connected_lawyers)}")
        #     for connected_lawyer in connected_lawyers:
        #         # print(f"Processing lawyer: {connected_lawyer.lawyer_email}")
        #         if connected_lawyer.lawyer_case_ids is not None:
        #             lawyer = self.get_lawpersonnel(connected_lawyer.lawyer_email)
        #             if lawyer:
        #                 lawyers.append(
        #                     {
        #                         "lawyer": lawyer.email,
        #                         "Point of Contact": f"{lawyer.full_legal_name}",
        #                         "Law Firm Name": getattr(lawyer, "law_firm_name", None),
        #                         "Experience": getattr(lawyer, "experience", None),
        #                         "Expertise": getattr(lawyer, "specialty", None),
        #                         "Main Office": getattr(
        #                             lawyer, "professional_address", None
        #                         ),
        #                         "Phone Number": getattr(lawyer, "contact_number", None),
        #                         "Image link": getattr(lawyer, "profile_picture", None),
        #                         "Email Address": getattr(lawyer, "email", None),
        #                         "Verified": (
        #                             getattr(lawyer, "verified", False)
        #                             if hasattr(lawyer, "verified")
        #                             else False
        #                         ),
        #                         "case_id": connected_lawyer.lawyer_case_ids,
        #                     }
        #                 )
        # if case_id is not None:
        #     db.close()
        #     result = [
        #         lawyer["lawyer"] for lawyer in lawyers if case_id in lawyer["case_id"]
        #     ]
        #     return result[0] if len(result) > 0 else None
        # elif only_emails:
        #     db.close()
        #     return [lawyer["lawyer"] for lawyer in lawyers]
        # else:
        #     db.close()
        #     return lawyers

        pass

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

    @staticmethod
    def get_case_checkout(
        self,
        case_type: str = "naturalization",
        debug: bool = False,
        user: Literal["immigrant", "lawpersonnel"] = "immigrant"
    ):
        # TODO: Connect with billing module
        pass

    @staticmethod
    def get_url_file_size(file_url: str) -> str:
        size = ""
        response = requests.head(file_url, timeout=10)
        response.raise_for_status()
        file_size = int(response.headers.get("Content-Length"))
        if file_size < 1024:
            size = f"{file_size} B"
        elif file_size < 1024**2:
            size = f"{file_size / 1024:.2f} KB"
        elif file_size < 1024**3:
            size = f"{file_size / 1024**2:.2f} MB"
        else:
            size = f"{file_size / 1024**3:.2f} GB"
        return size

    @staticmethod
    def create_dummy_upload(local_file_path: str) -> UploadFile_Dummy:
        if local_file_path.startswith("http"):
            response = requests.head(local_file_path, timeout=10)
            response.raise_for_status()
            file_size = int(response.headers.get("Content-Length"))
        else:
            file_size = os.path.getsize(local_file_path)
        content_type, _ = mimetypes.guess_type(local_file_path)
        local_file = UploadFile_Dummy(size=file_size, content_type=content_type)
        return local_file

    @staticmethod
    def get_file_size(file_size: int) -> str:
        # print(file_size)
        if file_size < 1024:
            return f"{file_size} B"
        elif file_size < 1024**2:
            return f"{file_size / 1024:.2f} KB"
        elif file_size < 1024**3:
            return f"{file_size / 1024**2:.2f} MB"
        else:
            return f"{file_size / 1024**3:.2f} GB"

    @staticmethod
    def store_file(
        file: Union[UploadFile, UploadFile_Dummy],
        file_url: str,
        email_id: EmailStr,
        filename: str,
        readable: bool = False,
    ) -> str:
        # TODO: Connect with Docs Service
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
