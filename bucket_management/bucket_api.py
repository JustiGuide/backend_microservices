import base64
import json
import mimetypes
from typing import Literal
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, HttpUrl
from email_gateway import Email
from helpers import Helpers
from .bucket_console import BucketConsole, DummyFile
from database import Functions
import os
from authorization import S3FileUrl, S3DirUrl, S3FileKey
from PIL import Image
import io

db_func = Functions()
app = APIRouter()
bucket = BucketConsole()


@app.post("/documents/upload")
async def upload_file(
    upload_file: UploadFile = File(...),
    bucket_directory: str = Form(...),
    is_previewable: bool = Form(True)
):
    file_content = await upload_file.read()
    filename, ext = os.path.splitext(upload_file.filename)
    file = DummyFile(
        content=file_content,
        size=upload_file.size,
        name=filename,
        ext=ext,
        content_type=upload_file.content_type
    )
    uploaded_url = bucket.upload_file(file=file, bucket_directory=bucket_directory, is_previewable=is_previewable)
    return {"url": uploaded_url}

class CrossChecking(BaseModel):
    destination: str = Form(...)
    filename: str = Form(...)

@app.post("/documents/cross-check")
async def cross_check_documents(payload: CrossChecking):
    file_key, new_filename = bucket.crosscheck_existing(
        destination_path=payload.destination,
        filename=payload.filename
    )
    return {"file_key": file_key, "filename": new_filename}

class RetrieveCaseDocs(BaseModel):
    immigrant_username: str = Form(...)
    lawyer_map: dict = Form(...)

@app.post("/documents/retrieve-case-documents")
async def retrieve_case_docs(payload: RetrieveCaseDocs):
    all_case_docs = bucket.retrieve_all_case_files(
        immigrant_username=payload.immigrant_username,
        lawyer_map=json.loads(payload.lawyer_map)
    )
    return JSONResponse(all_case_docs)

class S3FileUrlInput(BaseModel):
    file_url: S3FileUrl

@app.post("/documents/download")
async def download_file(payload: S3FileUrlInput):
    file_contents = bucket.download_file(payload.file_url)
    if "image_data" in file_contents:
        file_data = file_contents.pop("image_data")
        file_contents["image_b64"] = base64.b64encode(file_data).decode("utf-8")
    
    return file_contents

class S3DirectoryUrlInput(BaseModel):
    directory: S3DirUrl

@app.post("/documents/delete-directory")
async def delete_directory(payload: S3DirectoryUrlInput):
    bucket.delete_user_directory(payload.directory)

@app.post("/documents/delete-file")
async def delete_file(payload: S3FileUrlInput):
    bucket.delete_user_file(payload.file_url)

@app.post("/documents/{user_type}/upload-profile-picture")
async def upload_profile_pic(profile_pic: UploadFile = File(...), username: str = Form(...), user_type: str = Literal["immigrants", "lawyers", "nonlawyers", "lawstudents", "paralegals"]):
    image_data = await profile_pic.read()
    image = Image.open(io.BytesIO(image_data))
    png_buffer = io.BytesIO()
    image.save(png_buffer, format="PNG")
    bucket.upload_new_profile_picture(file_data=png_buffer.getvalue(), user_type=user_type, username=username)

class ImmigrantFileRetrieval(BaseModel):
    immigrant_username: str

@app.post("/documents/retrieve/immigrant-files")
async def retrieve_immigrant_files(payload: ImmigrantFileRetrieval):
    all_file_urls = bucket.retrieve_all_immigrant_files(payload.immigrant_username)
    return JSONResponse(all_file_urls)

class VerificationItems(BaseModel):
    lawpersonnel_username: str = Form(...)
    professional_license: UploadFile = File(None)
    address_proof: UploadFile = File(None)
    government_id: UploadFile = File(...)

@app.post("/documents/{user_type}/add-verification-items")
async def add_lawpersonnel_ver_items(
    lawpersonnel_username: str = Form(...),
    professional_license: UploadFile = File(None),
    address_proof: UploadFile = File(None),
    government_id: UploadFile = File(...),
    user_type: str = Literal["lawyers", "nonlawyers", "lawstudents", "paralegals"]
):
    
    government_id_data = await government_id.read()
    government_id_filename = government_id.filename
    if user_type == "lawyer":
        professional_license_data = await professional_license.read()
        professional_license_filename = professional_license.filename
        address_proof_data = await address_proof.read()
        address_proof_filename = address_proof.filename
        license_url, proof_url = bucket.add_lawyer_verification_items(lawyer_username=lawpersonnel_username, professional_license_contents=professional_license_data, professional_license_filename=professional_license_filename, address_proof_contents=address_proof_data, address_proof_filename=address_proof_filename)

    government_id_url = bucket.add_government_id(lawpersonnel_username=lawpersonnel_username, lawpersonnel_type=user_type, government_id_contents=government_id_data, government_id_filename=government_id_filename)

    return {
        "license_url": license_url,
        "proof_url": proof_url,
        "gov_id_url": government_id_url
    }

class S3DirectoryRename(BaseModel):
    old_directory: S3DirUrl = Form(...)
    new_directory: S3DirUrl = Form(...)

@app.post("/documents/rename-directory")
async def rename_user_directory(payload: S3DirectoryRename):
    bucket.rename_directory(old_directory=payload.old_directory, new_directory=payload.new_directory)

class DirectoryCreation(BaseModel):
    username: str = Form(...)


@app.post("/documents/{user_type}/create-directories")
async def create_user_directory(
    payload: DirectoryCreation,
    user_type: str = Literal[
        "immigrants", "lawyers", "nonlawyers", "lawstudents", "paralegals"
    ],
):
    bucket.create_directory(
        username=payload.username, user_type=user_type
    )

@app.post("/documents/delete-directory")
async def delete_user_directory(payload: S3DirectoryUrlInput):
    bucket.delete_user_directory(directory_url=payload.directory)


@app.post("/documents/delete-file")
async def delete_user_file(payload: S3FileUrlInput):
    bucket.delete_user_file(file_url=payload.file_url)

class MoveFile(BaseModel):
    file_url: S3FileUrl
    new_dir: S3DirUrl

@app.post("/documents/move-file")
async def move_user_file(payload: MoveFile):
    bucket.move_user_file(file_url=payload.file_url, new_directory=payload.new_dir)

class WebTransfer(BaseModel):
    web_url: HttpUrl = Form(...)
    file_key: S3FileKey = Form(...)

@app.post("/documents/transfer-web-file")
async def transfer_web_file(payload: WebTransfer):

    bucket_file_url = bucket.upload_web_file(web_url=str(payload.web_url), file_key=payload.file_key)
    return {"new_url": bucket_file_url}

@app.post("/documents/{user_type}/upload-to-case")
async def upload_case_documents(
    document_list: list[UploadFile] = File(...),
    lawpersonnel_email: EmailStr = Form(...),
    client_email: EmailStr = Form(...),
    user_type: str = Literal[
        "immigrant", "lawyer", "nonlawyer", "lawstudent", "paralegal"
    ],
    case_id: str = Form(...),
    folder_name: str = Form(...)
):
    lawpersonnel = db_func.get_lawpersonnel(lawpersonnel_email)
    client = db_func.get_immigrant(client_email)
    is_sender_client = user_type == "immigrants"
    file_sender = client if is_sender_client else lawpersonnel
    destination_dir = f"{lawpersonnel.personnel_type}/{lawpersonnel.username}/{case_id}/{folder_name}"
    file_count = 0
    response = {}
    assignees, client_email = db_func.retrieve_specific_case(
        lawpersonnel.email, case_id
    )
    if not db_func.check_if_paid(case_id):
        case_type = db_func.retrieve_case_type(lawpersonnel.email, case_id)
        case_checkoutId = Helpers.get_case_checkout(
            case_type, "lawpersonnel"
        )
        Helpers.add_notification(
            receiver=lawpersonnel.email,
            sender=client.email,
            type="case_payment",
            content=f"Please complete the case payment to upload documents for case #{case_id}",
            target_id={"case_checkout": case_checkoutId, "case_id": case_id},
        )
        Email.send_case_creation(
            f"{lawpersonnel.full_legal_name}",
            lawpersonnel.email,
            f"{lawpersonnel.full_legal_name}",
            case_checkoutId,
            case_id,
        )
        raise HTTPException(
            status_code=403,
            detail="This case is not paid for. Please pay to upload documents.",
        )
    for file in document_list:
        if file.filename != "blob":
            filename, ext = os.path.splitext(Helpers.get_legal_filename(file.filename))
            content_type, _ = mimetypes.guess_type(filename)
            file_contents = await file.read()
            document = DummyFile(
                content=file_contents,
                size=len(file_contents),
                name=filename,
                ext=ext,
                content_type=content_type
            )
            file_url = bucket.upload_file(
                file=document, bucket_directory=destination_dir
            )
            db_func.add_lawpersonnel_filedetails(lawpersonnel_email=lawpersonnel.email, file_url=file_url, file_type="case_docs")
            file_count += 1
            filename, document_url, file_id = db_func.add_case_document(
                lawyer_email=lawpersonnel.email,
                case_id=case_id,
                document_url=file_url,
                filename=filename,
                folder_name=folder_name,
            )
            response[filename] = {"url": document_url, "id": file_id}

    role = lawpersonnel.personnel_type.capitalize() if not is_sender_client else "Client"
    plural_str = "file"
    if file_count > 1:
        plural_str += "s"
    db_func.add_recent_action(
        lawyer_email=lawpersonnel.email,
        case_id=case_id,
        action=f"has added {file_count} {plural_str} to {folder_name}",
        actor=f"{file_sender.full_legal_name}",
        role=role,
    )
    if folder_name == "chat":
        Helpers.add_notification(
            receiver=client.email if is_sender_client else lawpersonnel.email,
            sender=file_sender.email,
            type="lawyer_chat",
            content=f"{file_sender.full_legal_name} has added {file_count} {plural_str} to {folder_name}",
            target_id={"sender": file_sender.email},
            one_time=True,
        )
    else:
        for assignee in assignees:
            Helpers.add_notification(
                receiver=assignee,
                sender=file_sender.email,
                type="cases",
                content=f"{file_sender.full_legal_name} has added {file_count} {plural_str} to {folder_name}",
                target_id={"case_id": case_id, "folder_name": folder_name},
            )
    return JSONResponse(response)

class FileListRetrieval(BaseModel):
    user_email: EmailStr
    file_type: Literal["ai_chat_files", "forms", "personal_files", "filled_forms", "case_docs"]
    case_id: str = None

@app.post("/documents/{user_type}/retrieve-specific")
async def retrieve_specific_filelist(
    payload: FileListRetrieval,
    user_type: str = Literal["immigrant", "lawyer", "nonlawyer", "lawstudent", "paralegal"]
):
    user = db_func.get_immigrant(payload.user_email) or db_func.get_lawpersonnel(payload.user_email)
    all_files = bucket.retrieve_all_immigrant_files(user.username) if user_type == "immigrant" else bucket.retrieve_all_lawpersonnel_files(user.username, f"{user.personnel_type}s")
    output_dict = []
    for file_url in all_files:
        file_object = db_func.retrieve_file(user_email=payload.user_email, file_url=file_url, user_type=user_type)
        if file_object.file_type == payload.file_type:
            filename = file_object.file_url.split("/")[-1]
            file_details = {"title": filename, "url": f"{os.getenv('BACKEND')}file/{file_object.uuid}", "size": Helpers.get_url_file_size(file_object.file_url)}
            if file_details not in output_dict:
                output_dict.append(file_details)

    return JSONResponse(output_dict)

class CaseFolderInput(BaseModel):
    immigrant_email: EmailStr
    lawpersonnel_email: EmailStr
    case_id: str
    folder_name: str


@app.post("/documents/{user_type}/retrieve-case-files")
async def retrieve_case_documents(
    payload: CaseFolderInput,
    user_type: str = Literal["immigrant", "lawyer", "nonlawyer", "lawstudent", "paralegal"]
):
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    is_actor_immigrant = True if user_type == "immigrant" else False
    all_documents=db_func.retrieve_case_documents(payload.lawpersonnel_email, payload.case_id, payload.folder_name)

    if not db_func.check_if_paid(payload.case_id):
        case_type = db_func.retrieve_case_type(lawpersonnel.email, payload.case_id)
        case_checkoutId = Helpers.get_case_checkout(case_type, "lawpersonnel")
        Helpers.add_notification(
            receiver=lawpersonnel.email,
            sender=immigrant.email,
            type="case_payment",
            content=f"Please complete the case payment to upload documents for case #{payload.case_id}",
            target_id={"case_checkout": case_checkoutId, "case_id": payload.case_id},
        )
        Email.send_case_creation(
            f"{lawpersonnel.full_legal_name}",
            lawpersonnel.email,
            f"{lawpersonnel.full_legal_name}",
            case_checkoutId,
            payload.case_id,
        )
        raise HTTPException(
            status_code=403,
            detail="This case is not paid for. Please pay to upload documents.",
        )
    documents = []
    for file_id in all_documents:
        all_documents[file_id]["id"] = file_id
        url = all_documents[file_id]["url"]
        file = Helpers.create_dummy_upload(url)
        all_documents[file_id]["size"] = Helpers.get_file_size(file.size)
        all_documents[file_id]["content_type"] = file.content_type
        documents.append(all_documents[file_id])

    return JSONResponse(documents)

class StorageCheck(BaseModel):
    immigrant_email: EmailStr


@app.post("/documents/immigrant/retrieve-storage-details/")
async def coveredStorage(
    payload: StorageCheck,
):
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    tier2storage = {
        "free": 1 * (1024**3),
        "pay": 1 * (1024**3),
        "plus": 10 * (1024**3),
        "enterprise": 100 * (1024**3),
    }
    if immigrant:
        used_storage = db_func.retrieve_used_storage(immigrant.email)
        coverPercent = used_storage / tier2storage[immigrant.subscription_type.lower()]
        return {"percent": coverPercent}
    else:
        return HTTPException(status_code=404, detail="User not found.")


"""
TODO:
/image/{file_id}/{filename}
/file/{file_id}/{filename}
"""
