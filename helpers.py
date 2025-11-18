from datetime import datetime
import string
import re
from typing import Any, Literal, Union
from pydantic import BaseModel, EmailStr
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
