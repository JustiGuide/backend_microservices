
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from database import Functions
from helpers import Helpers
from documents_gateway import DocumentsGateway
from .verifier_agent import LawPersonnelVerifier
from email_gateway import Email

db_func = Functions()
docs = DocumentsGateway()
verifier = LawPersonnelVerifier()

app = APIRouter()

@app.post("/verifier/lawpersonnel/verify/{lawpersonnel_username}")
async def verify_lawpersonnel(lawpersonnel_username: str):
    lawpersonnel = db_func.get_lawpersonnel(lawpersonnel_username)
    if lawpersonnel.verified:
        return JSONResponse({"success": True})

    verification_items = db_func.retrieve_lawpersonnel_verification_items(lawpersonnel_email=lawpersonnel.email, lawpersonnel_type=lawpersonnel.personnel_type)

    govt_id_url = verification_items[0].get("government_id", None)
    govt_id_type = verification_items[0].get("government_id_type", None)
    file_data = docs.download_file(govt_id_url) if govt_id_url else None

    if file_data and Helpers.is_image_file(file_data["filename"]):
        govt_id_bytes = file_data["image_data"]
    else:
        govt_id_bytes = file_data["content"]

    file_bytes = {
        "government_id": govt_id_bytes,
        # "professional_licenses": verification_items["professional_licenses"],
        # "address_proofs": verification_items["address_documents"],
    }
    provided_data = {
        "full_legal_name": lawpersonnel.full_legal_name,
        "date_of_birth": lawpersonnel.date_of_birth,
        "id_type": govt_id_type,
    }
    if lawpersonnel.personnel_type == "lawyer":
        provided_data["bar_id"] = lawpersonnel.details["bar_association"]
    is_verified, verification_error = verifier._run_verification(
        file_bytes=file_bytes, provided_data=provided_data
    )
    if is_verified:
        db_func.verify_lawpersonnel(lawpersonnel.email)
        Email.send_verification_success_email(
            lawpersonnel.username,
        )
        return JSONResponse({"success": True})

    else:
        user_dir = f"{lawpersonnel.personnel_type}/{lawpersonnel.username}/"
        Email.send_verification_failed_email(
            lawpersonnel.username
        )
        db_func.delete_lawpersonnel_verification_items(
            lawpersonnel_email=lawpersonnel.email,
            lawpersonnel_type=lawpersonnel.personnel_type,
        )
        db_func.delete_lawpersonnel_info(
            lawpersonnel_email=lawpersonnel.email,
            lawpersonnel_type=lawpersonnel.personnel_type,
        )
        db_func.delete_lawpersonnel(lawpersonnel.email)
        docs.delete_dir(user_dir)
        return JSONResponse({"success": False})
