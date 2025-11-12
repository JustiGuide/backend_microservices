import os
from typing import Literal
from fastapi import Depends, File, Form, HTTPException, UploadFile, APIRouter, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from authorization import (
    Authorizer,
    FormNameValidator,
)
from database import Functions
from helpers import Helpers
from documents_gateway import DocumentsGateway
from pathlib import Path
from background_utility import BackgroundUtilities
from .compiler_agent import Compiler, DocumentCompiler
from dotenv import load_dotenv

load_dotenv()

db_func = Functions()
docs = DocumentsGateway()
compiler = Compiler()

app = APIRouter()

class ImmigrantCompilerInput(BaseModel):
    immigrant_username: str
    form_name: FormNameValidator

class LawpersonnelCompilerInput(BaseModel):
    lawpersonnel_username: str
    immigrant_email: EmailStr = Depends(Authorizer.client_email_validator)
    form_name: FormNameValidator
    specific_case_id: str = None

@app.post("/app-compiler/immigrant/start-compiler")
async def immigrant_start_compiling(payload: ImmigrantCompilerInput, background_tasks: BackgroundTasks):
    immigrant = db_func.get_immigrant(payload.immigrant_username)
    case_type = Helpers.get_casetype(payload.form_name)
    lawyer_map = {
        db_func.get_lawpersonnel(lawyer["lawyer"]).username: lawyer["case_id"]
        for lawyer in Helpers.retrieve_connected_lawyers(immigrant_email=immigrant.email)
    }

    form_obj = None
    checklist = None
    to_create_checklist = False
    required_documents_list = None
    is_checked = db_func.is_checklist_checked(immigrant_email=immigrant.email, form_name=payload.form_name)
    required_documents = db_func.get_application_checklist(immigrant_email=immigrant.email, form_name=payload)
    if len(required_documents) > 0 and required_documents[0]["document_name"] != "Error":
        required_documents_list = [doc["document_name"] for doc in required_documents]
        checklist = db_func.check_compiler_status(email=immigrant.email, case_type=case_type, checklist=required_documents_list)
    else:
        to_create_checklist = True

    is_compiled = False
    compile_ready = False
    if not checklist and not is_checked:
        background_tasks.add_task(
            run_in_threadpool,
            BackgroundUtilities.start_compiler,
            immigrant_username=immigrant.username,
            lawyer_map=lawyer_map,
            case_type=case_type,
            form_name=payload.form_name,
            to_create_checklist=to_create_checklist,
        )
        return JSONResponse(
            {
                "checklist": required_documents_list,
                "analysis_report": [],
                "compile_ready": False,
                "is_compiled": False,
                "compiled_form": form_obj,
                "message": "Compilation started, please check back later.",
            }
        )

    else:
        checklist = db_func.check_compiler_status(
            email=immigrant.email, case_type=case_type, checklist=required_documents_list
        )
        analysis_report = [
            {
                "document_name": document,
                "file_url": checklist[document]["file_url"],
                "status": checklist[document]["status"],
                "file_size": checklist[document]["file_size"],
                "replace_reasons": checklist[document]["replace_reasons"],
            }
            for document in checklist
        ]

    compiled_form = f"https://doloreschatbucket.s3.us-east-2.amazonaws.com/immigrants/{immigrant.username}/forms/{payload.form_name}_compiled_application.pdf"
    compiled_id = db_func.retrieve_file(compiled_form, immigrant.email).uuid
    act_compiled_form = f"{os.getenv('BACKEND')}file/{compiled_id}/{payload.form_name}_compiled_application.pdf"
    if docs.is_exists(compiled_form):
        is_compiled = True

    if all(doc["status"]=="Present" for doc in analysis_report):
        compile_ready = True
        form_obj = {
            "filename": f"{payload.form_name}_compiled_application.pdf",
            "file_url": act_compiled_form,
        }

    return JSONResponse(
        {
            "checklist": required_documents_list,
            "analysis_report": analysis_report,
            "compile_ready": compile_ready,
            "is_compiled": is_compiled,
            "compiled_form": form_obj,
            "message": "Compilation completed successfully.",
        }
    )


@app.post("/app-compiler/lawpersonnel/start-compiler")
async def lawpersonnel_start_compiling(
    payload: LawpersonnelCompilerInput, background_tasks: BackgroundTasks
):
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_username)
    case_type = Helpers.get_casetype(payload.form_name)
    client_cases = db_func.retrieve_client_cases(lawpersonnel_email=lawpersonnel.email, client_email=immigrant.email)
    lawyer_cases = [
        case["id"]
        for case in client_cases
        if db_func.retrieve_case_type(lawpersonnel.email, case["id"]) == case_type
    ]
    lawyer_map = {lawpersonnel.username: lawyer_cases}
    accepted_forms = [
        Helpers.get_formname_from_case(db_func.retrieve_case_type(lawpersonnel_email=lawpersonnel.email, case_id=case["id"])) for case in client_cases
    ]
    if payload.form_name not in accepted_forms:
        raise HTTPException(
            status_code=400, detail="Case type not accepted for this lawyer."
        )
    checklist = None
    to_create_checklist = False
    required_documents_list = None
    is_checked = db_func.is_checklist_checked(
        immigrant_email=immigrant.email, form_name=payload.form_name
    )
    required_documents = db_func.get_application_checklist(
        immigrant_email=immigrant.email, form_name=payload.form_name
    )
    if (
        len(required_documents) > 0
        and required_documents[0]["document_name"] != "Error"
    ):
        required_documents_list = [doc["document_name"] for doc in required_documents]
        checklist = db_func.check_compiler_status(
            email=immigrant.email,
            case_type=case_type,
            checklist=required_documents_list,
        )
    else:
        to_create_checklist = True

    form_obj = None
    is_compiled = False
    compile_ready = False
    if not checklist and not is_checked:
        background_tasks.add_task(
            run_in_threadpool,
            BackgroundUtilities.start_compiler,
            immigrant_username=immigrant.username,
            lawyer_map=lawyer_map,
            case_type=case_type,
            form_name=payload.form_name,
            to_create_checklist=to_create_checklist,
            lawyer_username=lawpersonnel.username,
        )
        return JSONResponse(
            {
                "checklist": required_documents_list,
                "analysis_report": [],
                "compile_ready": False,
                "is_compiled": False,
                "compiled_form": form_obj,
                "message": "Compilation started, please check back later.",
            }
        )
    else:

        checklist = db_func.check_compiler_status(
            email=immigrant.email,
            case_type=case_type,
            checklist=required_documents_list,
        )
        analysis_report = [
            {
                "document_name": document,
                "file_url": checklist[document]["file_url"],
                "status": checklist[document]["status"],
                "file_size": checklist[document]["file_size"],
                "replace_reasons": checklist[document]["replace_reasons"],
            }
            for document in checklist
        ]

    compiled_form = f"https://doloreschatbucket.s3.us-east-2.amazonaws.com/immigrants/{immigrant.username}/forms/{payload.form_name}_compiled_application.pdf"

    if docs.is_exists(compiled_form):
        is_compiled = True
        form_obj = {
            "filename": f"{payload.form_name}_compiled_application.pdf",
            "file_url": compiled_form,
        }

    if all(doc["status"] == "Present" for doc in analysis_report):
        compile_ready = True

    return JSONResponse(
        {
            "checklist": required_documents_list,
            "analysis_report": analysis_report,
            "compile_ready": compile_ready,
            "is_compiled": is_compiled,
            "compiled_form": form_obj,
            "message": "Compilation completed successfully.",
        }
    )


@app.post("/app-compiler/immigrant/upload-compiler-document")
async def upload_immigrant_compiler_document(
    file: UploadFile = File(...),
    file_checklist: str = Form(...),
    form_name: FormNameValidator = Form(...),
    immigrant_username: str = Form(...),
    is_replace: bool = Form(...),
):
    immigrant = db_func.get_immigrant(immigrant_username)
    case_type = Helpers.get_casetype(form_name)

    lawyer_map = {
        db_func.get_lawpersonnel(lawyer["lawyer"]).username: lawyer["case_id"]
        for lawyer in Helpers.retrieve_connected_lawyers(
            immigrant_email=immigrant.email
        )
    }
    case_ids = []
    for lawyer in lawyer_map:
        lawyer_obj = db_func.get_lawpersonnel(lawyer)
        for case in lawyer_map[lawyer]:
            if (
                db_func.retrieve_case_type(lawyer_email=lawyer_obj.email, case_id=case)
                == case_type
            ):
                case_ids.append(case)

    if len(case_ids) == 0:
        case_ids = [None]
    if file.filename == "blob":
        raise HTTPException(status_code=400, detail="Invalid file")
    destination_dir = f"immigrants/{immigrant.username}/files"
    tmp_filename = Helpers.get_legal_filename(file.filename)
    temp_file_path = Path("/tmp") / tmp_filename
    temp_file_path.parent.mkdir(parents=True, exist_ok=True)
    s3_key, upd_file_name = docs.crosscheck_existing(destination_dir, tmp_filename)
    with open(temp_file_path, "wb") as temp_file:
        content = await file.read()
        temp_file.write(content)

    file_url = docs.upload_file(str(temp_file_path), s3_key)

    _ = Helpers.store_file(
        file=file,
        file_url=file_url,
        email_id=immigrant.email,
        filename=upd_file_name,
    )
    db_func.add_immigrant_filedetails(immigrant.email, file_url, "files")
    os.remove(str(temp_file_path))
    file_details = docs.download_file(file_url)
    file_details["file_url"] = file_url
    required_checklist = db_func.get_application_checklist(
        immigrant_email=immigrant.email, form_name=form_name
    )
    file_checklist_item = [
        required_checklist_item
        for required_checklist_item in required_checklist
        if required_checklist_item["document_name"] == file_checklist
    ]
    if not file_checklist_item:
        raise HTTPException(status_code=400, detail="Invalid checklist item")
    to_test = False
    if immigrant.username in ["enejivic", "rajanpande", "rajpatelh1b"]:
        to_test = True

    result = compiler.check_specific_file(
        checklist_item=file_checklist_item, file_details=file_details, is_test=to_test
    )
    if result["status"] in ["Present", "Replace"]:
        to_replace = False
        replace_reasons = None
        if result["status"] == "Replace":
            to_replace = True
            replace_reasons = result.get("reason", None)
        for case_id in case_ids:
            if is_replace:
                db_func.replace_compiler_document(
                    email=immigrant.email,
                    case_type=case_type,
                    case_id=case_id,
                    file_type=file_checklist,
                    file_url=file_url,
                    to_replace=to_replace,
                    replace_reasons=replace_reasons,
                )
            else:
                db_func.add_compiler_document(
                    email=immigrant.email,
                    case_id=case_id,
                    case_type=case_type,
                    file_type=file_checklist,
                    file_url=file_url,
                    to_replace=to_replace,
                    replace_reasons=replace_reasons,
                )

    return JSONResponse(
        {
            "document_name": file_checklist,
            "file_url": file_url,
            "status": result["status"],
            "file_size": Helpers.get_url_file_size(file_url),
            "replace_reasons": result.get("reason", None),
        }
    )


@app.post("/app-compiler/lawpersonnel/upload-compiler-document")
async def upload_lawyer_compiler_document(
    file: UploadFile = File(...),
    file_checklist: str = Form(...),
    form_name: FormNameValidator = Form(...),
    lawpersonnel_username: str = Form(...),
    immigrant_email: str = Depends(Authorizer.client_email_validator),
    is_replace: bool = Form(False),
    specific_case_id: str = Form(None),
):
    immigrant = db_func.get_immigrant(immigrant_email)
    lawpersonnel = db_func.get_lawpersonnel(lawpersonnel_username)
    case_type = Helpers.get_casetype(form_name)
    client_cases = db_func.retrieve_client_cases(
        lawpersonnel_email=lawpersonnel.email, client_email=immigrant.email
    )
    lawyer_cases = [
        case["id"]
        for case in client_cases
        if db_func.retrieve_case_type(lawpersonnel.email, case["id"]) == case_type
    ]
    lawyer_map = {lawpersonnel.username: lawyer_cases}
    if specific_case_id and specific_case_id not in lawyer_cases:
        raise HTTPException(
            status_code=404, detail="Specific case ID not found for this lawyer."
        )
    case_ids = []
    for lawyer_user in lawyer_map:
        case_ids.extend(lawyer_map[lawyer_user])
    if file.filename == "blob":
        raise HTTPException(status_code=400, detail="Invalid file")
    last_file_url = None
    case_files = {}
    tmp_filename = Helpers.get_legal_filename(file.filename)
    temp_file_path = Path("/tmp") / tmp_filename
    temp_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_file_path, "wb") as temp_file:
        content = await file.read()
        temp_file.write(content)

    for case_id in case_ids:
        destination_dir = f"{lawpersonnel.personnel_type}s/{lawpersonnel.username}/{case_id}/Case Documents"
        s3_key, upd_file_name = docs.crosscheck_existing(destination_dir, tmp_filename)
        file_url = docs.upload_file(str(temp_file_path), s3_key)
        # file_url = s3.upload_previewable(str(temp_file_path), s3_key)

        _ = Helpers.store_file(
            file=file,
            file_url=file_url,
            email_id=immigrant.email,
            filename=upd_file_name,
        )

        case_files[case_id] = file_url
        db_func.add_case_document(
            lawyer_email=lawpersonnel.email,
            case_id=case_id,
            document_url=file_url,
            filename=upd_file_name,
            folder_name="Case Documents",
        )
        os.remove(str(temp_file_path))
        if specific_case_id and specific_case_id == case_id:
            last_file_url = file_url
    if not last_file_url:
        last_file_url = file_url
    file_details = docs.download_file(last_file_url)
    file_details["file_url"] = last_file_url
    required_checklist = db_func.get_application_checklist(
        immigrant_email=immigrant.email, form_name=form_name
    )
    file_checklist_item = [
        required_checklist_item
        for required_checklist_item in required_checklist
        if required_checklist_item["document_name"] == file_checklist
    ]
    result = compiler.check_specific_file(
        checklist_item=file_checklist_item, file_details=file_details
    )
    if result["status"] in ["Present", "Replace"]:
        to_replace = False
        replace_reasons = None
        if result["status"] == "Replace":
            to_replace = True
            replace_reasons = result.get("reason", None)
        for case_id in case_ids:
            if is_replace:
                db_func.replace_compiler_document(
                    email=immigrant.email,
                    case_type=case_type,
                    file_type=file_checklist,
                    file_url=case_files[case_id],
                    to_replace=to_replace,
                    replace_reasons=replace_reasons,
                )
            else:
                db_func.add_compiler_document(
                    email=immigrant.email,
                    case_id=case_id,
                    case_type=case_type,
                    file_type=file_checklist,
                    file_url=case_files[case_id],
                    to_replace=to_replace,
                    replace_reasons=replace_reasons,
                )

    return JSONResponse(
        {
            "document_name": file_checklist,
            "file_url": last_file_url,
            "status": result["status"],
            "file_size": Helpers.get_url_file_size(last_file_url),
            "replace_reasons": result.get("reason", None),
        }
    )

@app.post("/app-compiler/immigrant/compile-application")
async def compile_immigrant_application(payload: ImmigrantCompilerInput):
    immigrant = db_func.get_immigrant(payload.immigrant_username)
    compiled_form = f"https://doloreschatbucket.s3.us-east-2.amazonaws.com/immigrants/{immigrant.username}/forms/{payload.form_name}_compiled_application.pdf"
    compiled_id = db_func.retrieve_file(compiled_form, immigrant.email).uuid
    act_compiled_form = f"{os.getenv('BACKEND')}file/{compiled_id}/{payload.form_name}_compiled_application.pdf"
    if docs.is_exists(compiled_form):
        return JSONResponse({
            "file_url": act_compiled_form,
            "message": "Application already compiled.",
            "output_filename": f"{payload.form_name}_compiled_application.pdf"
        })
    case_type = Helpers.get_casetype(payload.form_name)
    checklist = db_func.get_case_matched_documents(email=immigrant.email, case_type=case_type)
    final_files_url = [[document["file_url"] for document in docs.get_all_compiler_documents(immigrant_username=immigrant.username, lawyer_map={})][-1]]
    for file in checklist:
        if checklist[file] not in final_files_url:
            final_files_url.append(checklist[file])
    output_filename = f"{payload.form_name}_compiled_application.pdf"
    doc_compiler = DocumentCompiler()
    output_file_path = f"./tmp/{output_filename}"
    success = doc_compiler.compile_from_s3_urls(
        s3_urls=final_files_url,
        output_path=output_file_path,
    )
    if success:
        destination_dir = f"immigrants/{immigrant.username}/forms"
        s3_key = f"{destination_dir}/{output_filename}"

        file_url = docs.upload_file(str(output_file_path), s3_key)
        dummy_file = Helpers.create_dummy_upload(local_file_path=file_url)
        compiled_id = Helpers.store_file(
            file=dummy_file,
            file_url=file_url,
            email_id=immigrant.email,
            filename=output_filename,
        )
        act_file_url = f"{os.getenv('BACKEND')}file/{compiled_id}/{output_filename}"
        doc_compiler._cleanup()
        return JSONResponse(
            {
                "file_url": act_file_url,
                "message": "Application compiled successfully.",
                "output_filename": output_filename,
            }
        )
    else:
        doc_compiler._cleanup()
        raise HTTPException(status_code=500, detail="Failed to compile application.")

@app.post("/app-compiler/lawpersonnel/compile-application")
async def compile_lawpersonnel_application(payload: LawpersonnelCompilerInput):
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_username)
    compiled_form = f"https://doloreschatbucket.s3.us-east-2.amazonaws.com/immigrants/{immigrant.username}/files/{payload.form_name}_compiled_application.pdf"
    compiled_id = db_func.retrieve_file(compiled_form, immigrant.email).uuid
    act_compiled_form = f"{os.getenv('BACKEND')}file/{compiled_id}/{payload.form_name}_compiled_application.pdf"
    if docs.is_exists(compiled_form):
        return JSONResponse(
            {
                "file_url": act_compiled_form,
                "message": "Application already compiled.",
                "output_filename": f"{payload.form_name}_compiled_application.pdf",
            }
        )
    case_type = Helpers.get_casetype(payload.form_name)
    client_cases = db_func.retrieve_client_cases(
        lawpersonnel_email=lawpersonnel.email, client_email=immigrant.email
    )
    lawyer_cases = [
        case["id"]
        for case in client_cases
        if db_func.retrieve_case_type(lawpersonnel.email, case["id"]) == case_type
    ]
    if payload.specific_case_id and payload.specific_case_id not in lawyer_cases:
        raise HTTPException(
            status_code=404, detail="Specific case ID not found for this lawyer."
        )
    checklist = db_func.get_case_matched_documents(
        email=immigrant.email, case_type=case_type, case_id=payload.specific_case_id
    )
    final_files_url = [
        [
            document["file_url"]
            for document in docs.get_all_compiler_documents(
                immigrant_username=immigrant.username, lawyer_map={}
            )
        ][-1]
    ]
    for file in checklist:
        if checklist[file] not in final_files_url:
            final_files_url.append(checklist[file])
    output_filename = f"{payload.form_name}_compiled_application.pdf"
    doc_compiler = DocumentCompiler()
    output_file_path = f"./tmp/{output_filename}"
    success = doc_compiler.compile_from_s3_urls(
        s3_urls=final_files_url,
        output_path=output_file_path,
    )
    if success:
        destination_dir = f"immigrants/{immigrant.username}/forms"
        s3_key = f"{destination_dir}/{output_filename}"

        file_url = docs.upload_file(str(output_file_path), s3_key)
        dummy_file = Helpers.create_dummy_upload(local_file_path=file_url)
        compiled_id = Helpers.store_file(
            file=dummy_file,
            file_url=file_url,
            email_id=immigrant.email,
            filename=output_filename,
        )
        act_file_url = f"{os.getenv('BACKEND')}file/{compiled_id}/{output_filename}"
        doc_compiler._cleanup()
        return JSONResponse(
            {
                "file_url": act_file_url,
                "message": "Application compiled successfully.",
                "output_filename": output_filename,
            }
        )
    else:
        doc_compiler._cleanup()
        raise HTTPException(status_code=500, detail="Failed to compile application.")

class MatchedDocumentInput(BaseModel):
    immigrant_username: str
    document_name: str
    document_url: str
    status: str = Literal["approved", "rejected"]
    form_name: FormNameValidator
    lawpersonnel_username: str = None
    specific_case_id: str = None

@app.post("/app-compiler/immigrant/verify-matched-document")
async def verify_immigrant_matched_document(payload: MatchedDocumentInput):
    immigrant = db_func.get_immigrant(payload.immigrant_username)
    case_type = Helpers.get_casetype(payload.form_name)
    db_func.change_document_status(
        email=immigrant.email,
        case_type=case_type,
        file_type=payload.document_name,
        file_url=payload.document_url,
        status=payload.status
    )
    return JSONResponse({
        "message": "Document verification status updated successfully"
    })


@app.post("/app-compiler/lawpersonnel/verify-matched-document")
async def verify_lawpersonnel_matched_document(payload: MatchedDocumentInput):
    immigrant = db_func.get_immigrant(payload.immigrant_username)
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_username)
    case_type = Helpers.get_casetype(payload.form_name)
    client_cases = db_func.retrieve_client_cases(
        lawpersonnel_email=lawpersonnel.email, client_email=immigrant.email
    )
    lawyer_cases = [
        case["id"]
        for case in client_cases
        if db_func.retrieve_case_type(lawpersonnel.email, case["id"]) == case_type
    ]
    if payload.specific_case_id and payload.specific_case_id not in lawyer_cases:
        raise HTTPException(
            status_code=404, detail="Specific case ID not found for this lawyer."
        )
    accepted_forms = [
        Helpers.get_formname_from_case(
            db_func.retrieve_case_type(
                lawpersonnel_email=lawpersonnel.email, case_id=case["id"]
            )
        )
        for case in client_cases
    ]
    if payload.form_name not in accepted_forms:
        raise HTTPException(status_code=400, detail="Case type not accepted for this lawpersonnel")

    db_func.change_document_status(
        email=immigrant.email,
        case_type=case_type,
        file_type=payload.document_name,
        file_url=payload.document_url,
        status=payload.status,
        case_id=payload.specific_case_id,
    )

    return JSONResponse(
        {"message": "Document verification status updated successfully."}
    )
