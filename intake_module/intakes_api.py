"""
TODO:
/intake/{form_id}
"""
from datetime import datetime, timezone
import hashlib
import io
import mimetypes
import os
import docx2pdf
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, EmailStr
import requests
from database import Functions
from documents_gateway import DummyFile, DocumentsGateway
from encryptor import Encrypt
from helpers import Helpers
from ai_gateway import AgentsGateway
from email_gateway import Email
from scheduler import TaskScheduler
from forms_gateway import FormsGateway, SignaturePositions
from PIL import Image
import tempfile
import docx2pdf

db_func = Functions()
app = APIRouter()
docs = DocumentsGateway()
agent = AgentsGateway()
forms = FormsGateway()
scheduler = TaskScheduler()

@app.post("/intake/lawpersonnel/upload-new")
async def upload_new_intake(
    lawpersonnel_email: EmailStr = Form(...), intake_form: UploadFile = File(...)
):
    lawpersonnel = db_func.get_lawpersonnel(lawpersonnel_email)
    intake_form_data = await intake_form.read()
    allowed_filename = Helpers.get_legal_filename(intake_form.filename)
    destination = f"{lawpersonnel.personnel_type}s/{lawpersonnel.username}/Intake+Forms"
    intake_filename, intake_ext = os.path.splitext(allowed_filename)
    intake_filetype, _ = mimetypes.guess_type(allowed_filename)
    intake_md5 = hashlib.md5(intake_form_data).hexdigest()
    if intake_form.filename != "blob" and not db_func.check_intake_md5(intake_md5, lawpersonnel.email):
        if intake_filetype != "application/pdf":
            if intake_filetype and intake_filetype.startswith("image/"):
                try:
                    image = Image.open(io.BytesIO(intake_form_data))
                    if image.mode in ("RGBA", "P"):
                        image = image.convert("RGB")

                    pdf_buffer = io.BytesIO()
                    image.save(pdf_buffer, "PDF")

                    intake_form_data = pdf_buffer.getvalue()
                    allowed_filename = f"{intake_filename}.pdf"
                except Exception as e:
                    raise HTTPException(
                        status_code=400, detail=f"Image conversion failed: {str(e)}"
                    )

            elif intake_ext in ["docx", "doc"]:
                with tempfile.TemporaryDirectory() as temp_dir:
                    input_path = os.path.join(temp_dir, f"input.{intake_ext}")
                    output_path = os.path.join(temp_dir, "output.pdf")
                    with open(input_path, "wb") as f:
                        f.write(intake_form_data)

                    try:
                        docx2pdf.convert(input_path, output_path)
                        with open(output_path, "rb") as f:
                            intake_form_data = f.read()

                        allowed_filename = f"{intake_filename}.pdf"
                    except Exception as e:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Document conversion failed: {str(e)}",
                        )

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format ({intake_ext}) for conversion.",
                )

        s3_directroy, final_filename = docs.crosscheck_existing(destination_path=destination, filename=allowed_filename)
        intake_form_file = DummyFile(
            content = intake_form_data,
            size = len(intake_form_data),
            name=intake_filename,
            ext="pdf",
            content_type="application/pdf"
        )
        file_url = docs.upload_file(file=intake_form_file, bucket_directory=s3_directroy)
        _ = Helpers.store_file(
            file=intake_form,
            file_url=file_url,
            email_id=lawpersonnel.email,
            filename=final_filename,
        )

    uploaded_form = db_func.upload_intake_form(file_url=file_url, lawyer_email=lawpersonnel.email, filename=allowed_filename, file_md5=intake_md5)
    return uploaded_form

class IntakeLawyer(BaseModel):
    lawpersonnel_email: EmailStr
    intake_form_id: str = None

@app.post("/intake/lawpersonnel/retrieve-forms")
async def retrieve_lawyer_forms(payload: IntakeLawyer):
    all_intake_forms = db_func.retrieve_forms(payload.lawpersonnel_email)
    return all_intake_forms

@app.post("/intake/lawpersonnel/remove-form")
async def remove_lawyer_form(payload: IntakeLawyer):
    is_success, form_url = db_func.delete_intake_form(lawyer_email=payload.lawpersonnel_email, form_id=payload.intake_form_id)
    if is_success:
        docs.delete_user_file(form_url)

class SendIntake(BaseModel):
    lawpersonnel_email: EmailStr
    immigrant_email: EmailStr
    case_id: str
    case_type: str
    form_id: str
    form_url: str

@app.post("/intake/lawpersonnel/send-form")
async def send_client_intake(payload: SendIntake):
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    date_sent = datetime.now(timezone.utc).date()
    db_func.add_client_intake(
        lawyer_email=payload.lawpersonnel_email,
        client_email=payload.immigrant_email,
        case_id=payload.case_id,
        case_type=payload.case_type,
        intake_form_id=payload.form_id,
        date_sent=date_sent,
        form_url=payload.form_url
    )
    Helpers.add_notification(
        receiver=immigrant.email,
        sender=lawpersonnel.email,
        type="intake",
        content=f"{lawpersonnel.full_legal_name} has sent you the intake form",
        target_id={"form_id": payload.form_id, "case_id": payload.case_id},
    )
    db_func.add_recent_action(
        lawpersonnel.email,
        payload.case_id,
        action=f"has sent the intake form to {immigrant.full_legal_name}",
        actor=f"{lawpersonnel.full_legal_name}",
        role=lawpersonnel.personnel_type.capitalize(),
    )

@app.post("/intake/immigrant/sign-intake")
async def sign_lawpersonnel_intake(
    background_tasks: BackgroundTasks,
    intake_id: str,
    case_id: str,
    immigrant_email: EmailStr,
    handshake_id: str
):
    intake_form_url, form_filename, lawpersonnel_email = db_func.retrieve_intake_form(intake_form_id=intake_id)
    response = requests.get(str(intake_form_url))
    if response.status_code != 200:
        raise HTTPException(
            status_code=400, detail="Failed to retrieve the intake form"
        )
    case = db_func.check_case(case_id)

    sign_positions = agent.get_signature_locations(intake_form_url)
    new_intake_form_url, date_signed = forms.sign_intake(intake_form_id=intake_id, signature_positions=SignaturePositions(positions=sign_positions), client_email=immigrant_email, lawpersonnel_email=lawpersonnel_email, sign_id=handshake_id)
    case_type = db_func.update_client_intake(case_id, date_signed, handshake_id)
    immigrant = db_func.get_immigrant(immigrant_email)
    lawpersonnel = db_func.get_lawpersonnel(lawpersonnel_email)
    case_checkoutId = Helpers.get_case_checkout(
        case_type=case_type, user="lawpersonnel"
    )
    Helpers.add_notification(
        receiver=lawpersonnel.email,
        sender=immigrant.email,
        type="case_payment",
        content=f"{immigrant.full_legal_name} has signed the intake form, please complete the case payment",
        target_id={"case_checkout": case_checkoutId, "case_id": case_id},
    )
    db_func.add_recent_action(
        lawpersonnel.email,
        case_id,
        action=f"has signed the intake form",
        actor=f"{immigrant.full_legal_name}",
        role="Client",
    )
    db_func.update_intake_form(
        lawpersonnel.email, intake_id, case_type, date_signed, new_intake_form_url
    )
    Email.send_case_creation(
        f"{lawpersonnel.full_legal_name}",
        lawpersonnel.email,
        f"{lawpersonnel.full_legal_name}",
        case_checkoutId,
        case_id,
    )
    tasks = db_func.retrieve_case_specific_tasks(lawpersonnel.email, case_id)
    if len(tasks) > 0:
        db_func.update_task_status(lawpersonnel.email, tasks[0]["id"], "Completed")
    payment_task_id = Encrypt.generate_uuid()

    payment_task_deadline_date, deadline_alertPrev, deadline_alertCurr = (
        Helpers.calculate_deadline(1)
    )
    case_name = db_func.retrieve_case_name(lawpersonnel.email, case_id)
    payment_task_details = {
        "id": payment_task_id,
        "name": f"Please complete the payment for the case",
        "visibility": "all",
        "case_name": case_name,
        "case_id": case_id,
        "assignee_list": [],
        "status": "To-Do",
        "deadline": payment_task_deadline_date,
        "document_list": [],
        "description": f"Please complete the payment using the link sent to your email",
    }
    db_func.add_task(lawyer_email=lawpersonnel.email, task_details=payment_task_details)

    Helpers.add_notification(
        receiver=lawpersonnel.email,
        sender=lawpersonnel.email,
        type="tasks",
        content=f"Task #{payment_task_id} deadline is almost near",
        target_id={"task_id": payment_task_id},
        one_time=True,
        created_at=deadline_alertPrev,
    )
    scheduler.schedule_task(
        Helpers.send_task_deadline,
        deadline_alertPrev,
        lawpersonnel.email,
        f"{lawpersonnel.full_legal_name}",
        payment_task_id,
        payment_task_details["name"],
        payment_task_details["description"],
        "in 1 day",
    )
    Helpers.add_notification(
        receiver=lawpersonnel.email,
        sender=lawpersonnel.email,
        type="tasks",
        content=f"Task #{payment_task_id} deadline is today",
        target_id={"task_id": payment_task_id},
        one_time=True,
        created_at=deadline_alertCurr,
    )
    scheduler.schedule_task(
        Helpers.send_task_deadline,
        deadline_alertCurr,
        lawpersonnel.email,
        f"{lawpersonnel.full_legal_name}",
        payment_task_id,
        payment_task_details["name"],
        payment_task_details["description"],
        "today",
    )
    background_tasks.add_task(
        run_in_threadpool,
        Helpers.remove_invitation,
        invL_bool=False,
        pendCl_bool=False,
        invEL_bool=False,
        lawyer=lawpersonnel,
        client=immigrant,
        case_id=case_id,
    )
    db_func.add_tasks_to_case([payment_task_id], case_id)
