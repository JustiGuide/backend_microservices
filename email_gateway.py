from pydantic import EmailStr
from database import LawPersonnel


class Email:
    @staticmethod
    def send_deadline_alert(lawyer: LawPersonnel, task_details: dict, deadline_type: str):
        # TODO: connect with email service
        pass
    
    @staticmethod
    def send_team_invitation(
        inviting_lawpersonnel: LawPersonnel,
        invited_lawpersonnel_email: EmailStr,
        invited_lawpersonnel_name: str,
    ):
        # TODO: connect with email service
        pass
