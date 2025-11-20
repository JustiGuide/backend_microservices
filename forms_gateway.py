from fastapi import UploadFile
from pydantic import BaseModel, EmailStr


class SignPos(BaseModel):
    page_number: int
    offsets: list[float]


class SignaturePositions(BaseModel):
    positions: list[SignPos]


class FormsGateway:
    def sign_intake(
        self,
        intake_form_id: str,
        signature_positions: SignaturePositions,
        client_email: EmailStr,
        lawpersonnel_email: EmailStr,
        sign_id: str
    ) -> tuple[str, str]:
        # TODO: connect with docs service
        pass
