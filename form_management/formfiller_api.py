
import json
import mimetypes
from pathlib import Path
import docx2pdf
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
import requests
from bucket_management.bucket_console import BucketConsole, DummyFile
from database import Functions
import os
from authorization import Authorizer, FormNameValidator
from PIL import Image
import io
from helpers import Helpers
from .formfiller_module import FormFiller

db_func = Functions()
app = APIRouter()
bucket = BucketConsole()
filler = FormFiller()

class StoreForm(BaseModel):
    form_owner: EmailStr = Form(...)
    form_details: dict = Form(...)
    form_name: FormNameValidator

@app.post("/forms/immigrants/store")
async def store_form(payload: StoreForm):
    form_data = json.loads(payload.form_details)
    if not filler.is_sign_id(form_data):
        return HTTPException(
            status_code=400, detail="No signature IDs found in form details"
        )

    immigrant = db_func.get_immigrant(payload.form_owner)

    db_func.add_form_details(form_name=payload.form_name, immigrant_email=payload.form_owner, form_data=form_data)

    output, legal_name = filler.fill_form(formname=payload.form_name, data_dict=form_data, user_email=payload.form_owner, full_legal_name="", is_signer=True)

    destination_dir = f"immigrants/{immigrant.username}/filled_forms"
    legal_file = Helpers.get_legal_filename(f"{legal_name}.pdf")
    file_key = f"{destination_dir}/{legal_file}"
    form_file = DummyFile(
        content=output,
        size=len(output),
        name=legal_file.removesuffix(".pdf"),
        ext="pdf",
        content_type="application/pdf"

    )
    form_url = bucket.upload_file(file=form_file, bucket_directory=file_key)
    file_id = db_func.store_file(file_name=legal_file, file_size=len(output), file_url=form_url, file_type="application/pdf", readable=True, email_id=immigrant.email)
    db_func.add_immigrant_filedetails(immigrant_email=immigrant.email, file_url=form_url, file_type="filled_forms")

    if payload.form_name not in filler.independent_cases:
        lawyers = Helpers.retrieve_connected_lawyers(immigrant_email=immigrant.email)
        cases = []
        for lawyer in lawyers:
            cases = lawyer["case_id"]
            if isinstance(cases, list) and len(cases) > 0:
                for case in cases:
                    case_type = db_func.retrieve_case_type(lawyer["lawyer"], case)
                    if case_type and db_func.get_all_casetypes()[case_type]["form"] == payload.form_name:
                        cases.append({"case_id": case, "lawyer": lawyer["lawyer"]})
        for lawyer_det in cases:
            db_func.add_recent_action(
                lawyer_email=lawyer_det["lawyer"],
                case_id=lawyer_det["case_id"],
                action=f"has sent the {payload.form_name} form",
                actor=f"{immigrant.full_legal_name}",
                role="Client",
            )
            Helpers.add_notification(
                receiver=lawyer_det["lawyer"],
                sender=immigrant.email,
                type="forms",
                content=f"{immigrant.full_legal_name} has sent the {payload.form_name} form",
                target_id={"client": immigrant.email, "form_name": payload.form_name},
            )

class RetrieveForm(BaseModel):
    form_owner: EmailStr = Form(...)
    form_name: FormNameValidator

@app.post("/forms/immigrants/retrieve")
async def retrieve_form_details(payload: RetrieveForm):
    form_details = db_func.retrieve_form_details(form_name=payload.form_name, immigrant_email=payload.form_owner)
    return JSONResponse(form_details)

class RetrieveClientForms(BaseModel):
    lawpersonnel_email: EmailStr
    immigrant_email: EmailStr = Depends(Authorizer.client_email_validator)
    form_name: FormNameValidator = None

@app.post("/forms/lawpersonnel/retrieve-available")
async def retrieve_available_forms(payload: RetrieveClientForms):
    available_forms = db_func.retrieve_available_forms(immigrant_email=payload.immigrant_email, lawyer_email=payload.lawpersonnel_email)
    return JSONResponse(available_forms)


@app.post("/forms/lawpersonnel/retrieve-specific")
async def retrieve_specific_forms(payload: RetrieveClientForms):
    available_forms = db_func.retrieve_available_forms(
        immigrant_email=payload.immigrant_email, lawyer_email=payload.lawpersonnel_email
    )
    if payload.form_name not in available_forms:
        return HTTPException(
            status_code=403, detail="This form is not available for this client."
        )
    return JSONResponse(available_forms[payload.form_name])

class ClientFormUpdate(BaseModel):
    immigrant_email: EmailStr = Depends(Authorizer.client_email_validator)
    form_name: FormNameValidator = Form(...)
    form_details: dict = Form(...)
    lawpersonnel_email: EmailStr = Form(...)

@app.post("/forms/lawpersonnel/send-form-update")
async def send_form_update(payload: ClientFormUpdate):
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_email)

    all_lawpersonnel = db_func.retrieve_connected_lawyers(immigrant_email=immigrant.email)
    cases = []
    for lawpersonnel_data in all_lawpersonnel:
        if lawpersonnel_data["lawyer"] == lawpersonnel.email:
            cases = lawpersonnel_data["case_id"]
            if isinstance(cases, list) and len(cases) > 0:
                for case in cases:
                    case_type = db_func.retrieve_case_type(
                        lawpersonnel_data["lawyer"], case
                    )
                    if case_type and db_func.get_all_casetypes()[case_type]["form"] == payload.form_name:
                        cases.append(case)

    for case_id in cases:
        db_func.add_recent_action(
            lawpersonnel.email,
            case_id,
            action=f"has made changes to the {payload.form_name} form",
            actor=f"{lawpersonnel.full_legal_name}",
            role=lawpersonnel.personnel_type.capitalize(),
        )
        Helpers.add_notification(
            receiver=immigrant.email,
            sender=lawpersonnel.email,
            type="forms",
            content=f"{lawpersonnel.full_legal_name} has made changes to the {payload.form_name} form",
            target_id={
                "lawyer_email": lawpersonnel.email,
                "form_name": payload.form_name,
            },
        )

@app.post("/forms/lawpersonnel/submit-form")
async def submit_form(payload: ClientFormUpdate):
    form_data = json.loads(payload.form_details) if payload.form_details else {}
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_email)

    all_lawpersonnel = db_func.retrieve_connected_lawyers(
        immigrant_email=immigrant.email
    )
    cases = []
    for lawpersonnel_data in all_lawpersonnel:
        if lawpersonnel_data["lawyer"] == lawpersonnel.email:
            cases = lawpersonnel_data["case_id"]
            if isinstance(cases, list) and len(cases) > 0:
                for case in cases:
                    case_type = db_func.retrieve_case_type(
                        lawpersonnel_data["lawyer"], case
                    )
                    if (
                        case_type
                        and db_func.get_all_casetypes()[case_type]["form"]
                        == payload.form_name
                    ):
                        cases.append({"case_id": case, "lawyer": lawpersonnel.email})
    if not filler.is_sign_id(form_data, check_lawyer=True):
        return HTTPException(status_code=404, detail="User Sign ID not attached")

    output, legal_name = filler.fill_form(
        formname=payload.form_name,
        data_dict=form_data,
        user_email=payload.immigrant_email,
        full_legal_name=immigrant.full_legal_name,
        is_signer=True,
        lawyer=lawpersonnel,
    )
    destination_dir = f"immigrants/{immigrant.username}/filled_forms"
    legal_file = Helpers.get_legal_filename(f"{legal_name}.pdf")
    file_key = f"{destination_dir}/{legal_file}"
    form_file = DummyFile(
        content=output,
        size=len(output),
        name=legal_file.removesuffix(".pdf"),
        ext="pdf",
        content_type="application/pdf",
    )
    form_url = bucket.upload_file(file=form_file, bucket_directory=file_key)
    file_id = db_func.store_file(
        file_name=legal_file,
        file_size=len(output),
        file_url=form_url,
        file_type="application/pdf",
        readable=True,
        email_id=immigrant.email,
    )
    db_func.add_immigrant_filedetails(
        immigrant_email=immigrant.email, file_url=form_url, file_type="filled_forms"
    )
    for case_details in cases:
        lawyer = db_func.get_lawpersonnel(case_details["lawyer_email"])
        db_func.update_lawyer_stat(lawyer.email, "submitted_forms")
        lawyer = db_func.get_lawpersonnel(lawyer.username)
        db_func.update_form_submission(lawyer.email, case_details["case_id"])
        db_func.add_recent_action(
            lawyer.email,
            case_details["case_id"],
            action=f"has submitted the {payload.form_name} form",
            actor=f"{lawyer.full_legal_name}",
            role=lawyer.personnel_type.capitalize(),
        )
        Helpers.add_notification(
            receiver=immigrant.email,
            sender=lawyer.email,
            type="forms",
            content=f"{lawyer.full_legal_name} has submitted the {payload.form_name} form",
            target_id={"lawyer_email": lawyer.email, "form_name": payload.form_name},
        )
        
    return {"uploaded": form_url}

class SignPos(BaseModel):
    page_number: int
    offsets: list[float]

class SignaturePositions(BaseModel):
    positions: list[SignPos]

class SignIntake(BaseModel):
    intake_form_id: str
    signature_positions: SignaturePositions
    client_email: EmailStr = Depends(Authorizer.client_email_validator)
    lawpersonnel_email: EmailStr
    sign_id: str = Depends(Authorizer.client_signid_validator)


@app.post("/forms/sign-pdf")
async def sign_pdf(payload: SignIntake):
    client = db_func.get_immigrant(payload.client_email)
    intake_form_url, filename = db_func.retrieve_intake_form(payload.intake_form_id)
    response = requests.get(str(intake_form_url))
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to retrieve the intake form")
    temp_file_path = Path("./temp") / filename
    temp_file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(temp_file_path, "wb") as f:
        f.write(response.content)
    content_type, _ = mimetypes.guess_type(str(temp_file_path))
    if content_type != 'application/pdf':
        if content_type.startswith('image/'):
            pdf_path = Path("./temp") / f"{os.path.splitext(filename)[0]}.pdf"
            image = Image.open(temp_file_path)
            image.convert('RGB').save(pdf_path, 'PDF')
            os.remove(temp_file_path)
            temp_file_path = str(pdf_path)
        elif filename.endswith('.docx') or filename.endswith('.doc'):
            pdf_path = Path("./temp") / f"{os.path.splitext(filename)[0]}.pdf"
            docx2pdf.convert(str(temp_file_path), str(pdf_path))
            os.remove(temp_file_path)
            temp_file_path = str(pdf_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format for conversion")

    output_file_path = Path("./temp") / f"signed_{filename}"
    sign_data = []
    for sign_position in payload.signature_positions.positions:
        sign_data.append({
            "sign_id": payload.sign_id,
            "target_page": sign_position.page_number,
            "offsets": sign_position.offsets
        })
    new_output, upd_filename = filler.sign_pdf(
        input_path=temp_file_path,
        output_path=str(output_file_path),
        user_email=payload.client_email,
        full_legal_name=client.full_legal_name,        
        sign_data=sign_data,
    )
    return FileResponse(
        path=new_output,
        filename=upd_filename,
        media_type="application/pdf"
    )

