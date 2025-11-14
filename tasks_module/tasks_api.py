import os
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from database import Functions
from authorization import (
    Authorizer,
    LawyerCaseID,
    TaskDetails,
    TaskVisibility,
    TaskStatus,
    DateString,
)
from encryptor import Encrypt
from helpers import Helpers
from scheduler import TaskScheduler
from documents_gateway import DocumentsGateway

db_func = Functions()
app = APIRouter()
scheduler = TaskScheduler()
docs = DocumentsGateway()

class TaskRetrievalInput(BaseModel):
    lawpersonnel_username: str

@app.post("/tasks/lawpersonnel/retrieve-all")
async def retrieve_all_tasks(payload: TaskRetrievalInput):
    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_username)
    case_details = db_func.get_all_tasks(lawyer.email)
    for task in case_details:
        all_assignees = set([])
        all_assignee_pps = set([])
        for assignee in task["assignee_list"]:
            assignee_obj = db_func.get_lawpersonnel(assignee)
            if assignee_obj:
                all_assignees.add(assignee_obj.email)
                all_assignee_pps.add(assignee_obj.profile_picture)
        task["assignee_list"] = list(all_assignees)
        task["assignee_profilePicUrls"] = list(all_assignee_pps)

    return JSONResponse(case_details)


@app.post("/tasks/lawpersonnel/create")
async def create_task(
    email_id: EmailStr = Form(...),
    task_name: str = Form(...),
    visibility: TaskVisibility = Form(...),
    case_id: str = Depends(Authorizer.validate_case_id_email),
    case_name: str = Depends(Authorizer.validate_case_name),
    assignee_list: list[EmailStr] = Form(...),
    status: TaskStatus = Form(...),
    deadline: DateString = Form(...),
    document_list: list[UploadFile] = File(...),
    description: str = Form(...)
):
    user = db_func.get_lawpersonnel(email_id)
    destination_dir = f"lawyers/{user.username.lower()}/{case_id}/Case Documents"
    file_urls = []
    for file in document_list:
        if file.filename != "blob":
            tmp_filename = Helpers.get_legal_filename(file.filename)
            temp_file_path = Path("./tmp") / tmp_filename
            temp_file_path.parent.mkdir(parents=True, exist_ok=True)
            s3_key, upd_file_name = docs.crosscheck_existing(
                destination_dir, tmp_filename
            )
            with open(temp_file_path, "wb") as temp_file:
                content = await file.read()
                temp_file.write(content)

            file_url = docs.upload_file(str(temp_file_path), s3_key)
            _ = Helpers.store_file(
                file=file,
                file_url=file_url,
                email_id=user.email,
                filename=upd_file_name,
            )
            file_urls.append(file_url)
            _, _, _ = db_func.add_case_document(
                lawyer_email=user.email,
                case_id=case_id,
                document_url=file_url,
                filename=tmp_filename,
                folder_name="Case Documents",
            )
            os.remove(str(temp_file_path))
    task_id = Encrypt.generate_uuid()
    task_details = {
        "id": task_id,
        "name": task_name,
        "visibility": visibility,
        "case_name": case_name,
        "case_id": case_id,
        "assignee_list": assignee_list,
        "status": status,
        "deadline": deadline,
        "document_list": file_urls,
        "description": description,
    }
    db_func.add_task(task_details=task_details, lawyer_email=user.email)
    db_func.add_tasks_to_case([task_id], case_id)
    role = user.personnel_type.capitalize()
    plural_str = "file"
    if len(file_urls) > 1:
        plural_str += "s"
    db_func.add_recent_action(
        user.email,
        case_id,
        f"has created task {task_name}",
        f"{user.full_legal_name}",
        role,
    )
    for receiver in assignee_list:
        rec_lawyer = db_func.get_lawpersonnel(receiver)
        Helpers.add_notification(
            receiver=rec_lawyer.email,
            sender=user.email,
            type="tasks",
            content=f"{user.full_legal_name} has created a task",
            target_id={"task_id": task_id},
        )

class TaskDetailInput(BaseModel):
    lawpersonnel_username: str
    task_id: str = Depends(Authorizer.taskid_validator)
    status: TaskStatus = None


@app.post("/tasks/lawpersonnel/retrieve-details")
async def retrieve_task_details(payload: TaskDetailInput):
    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_username)
    task = db_func.retrieve_task(lawyer_email=lawyer.email, task_id=payload.task_id)
    if len(list(task.keys())) > 0:
        return JSONResponse(task)
    else:
        return {"error": "Case Not Found"}


@app.post("/tasks/lawpersonnel/update-status")
async def update_task_status(
    payload: TaskDetailInput,
):

    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_username)
    rows, task_name, case_id = db_func.update_task_status(
        lawyer_email=lawyer.email, task_id=payload.task_id, status=payload.status
    )
    taskDetails = db_func.retrieve_task(
        lawyer_email=lawyer.email, task_id=payload.task_id
    )
    role = lawyer.personnel_type.capitalize()
    db_func.add_recent_action(
        lawyer_email=lawyer.email,
        case_id=case_id,
        action=f"has updated the {task_name} status to {payload.status}",
        actor=f"{lawyer.full_legal_name}",
        role=role,
    )
    assignees = taskDetails["assignee_list"]
    for receiver in assignees:
        rec_lawyer = db_func.get_lawpersonnel(receiver)
        Helpers.add_notification(
            receiver=rec_lawyer.email,
            sender=lawyer.email,
            type="tasks",
            content=f"{lawyer.full_legal_name} has updated the task status for task {payload.task_id}",
            target_id={"task_id": payload.task_id},
        )
    if rows == 1:
        return {"updated": True}
    else:
        return {"updated": False}


class TaskSchema(BaseModel):
    username: str
    task_id: str
    docs_to_delete: list[str] = None
    assignees_to_remove: list[EmailStr] = None
    case_id: str
    assignees_to_add: list[EmailStr] = None
    task_name: str = None
    visibility: TaskVisibility = None
    status: TaskStatus = None
    deadline: DateString = None
    description: str = None


@app.post("/tasks/lawpersonnel/update")
async def update_task_details(
    details: TaskDetails = Form(...), document_list: list[UploadFile] = File(...)
):
    details: TaskSchema = details
    lawyer = db_func.get_lawpersonnel(details.username)
    taskDetails = db_func.retrieve_task(
        lawyer_email=lawyer.email, task_id=details.task_id
    )
    current_documents = list(taskDetails.get("document_list", []))
    if details.docs_to_delete is not None:
        docs_to_delete_set = set(str(url) for url in details.docs_to_delete)
        current_documents = [
            doc for doc in current_documents if str(doc) not in docs_to_delete_set
        ]
        for doc_url in details.docs_to_delete:
            docs.delete_file(str(doc_url))

    current_assignees = list(taskDetails.get("assignee_list", []))
    if details.assignees_to_remove is not None:
        assignees_to_remove_set = set(details.assignees_to_remove)
        current_assignees = [
            assignee
            for assignee in current_assignees
            if assignee not in assignees_to_remove_set
        ]

    if details.assignees_to_add is not None:
        for assignee_to_add in details.assignees_to_add:
            if assignee_to_add not in current_assignees:
                current_assignees.append(assignee_to_add)

    for file in document_list:
        if file.filename != "blob":
            destination_dir = (
                f"lawyers/{lawyer.username.lower()}/{details.case_id}/Case Documents"
            )
            tmp_filename = Helpers.get_legal_filename(file.filename)
            temp_file_path = Path("./tmp") / tmp_filename
            temp_file_path.parent.mkdir(parents=True, exist_ok=True)
            s3_key, upd_file_name = docs.crosscheck_existing(destination_dir, tmp_filename)
            with open(temp_file_path, "wb") as temp_file:
                content = await file.read()
                temp_file.write(content)

            file_url = docs.upload_file(str(temp_file_path), s3_key)

            _ = Helpers.store_file(
                file=file,
                file_url=file_url,
                email_id=lawyer.email,
                filename=upd_file_name,
            )
            current_documents.append(file_url)
            _, _, _ = db_func.add_case_document(
                lawyer_email=lawyer.email,
                case_id=details.case_id,
                document_url=file_url,
                filename=tmp_filename,
                folder_name="Case Documents",
            )
            os.remove(str(temp_file_path))

    updated_task_details = taskDetails.copy()
    if details.task_name is not None:
        updated_task_details["name"] = details.task_name
    if details.visibility is not None:
        updated_task_details["visibility"] = details.visibility
    if details.status is not None:
        updated_task_details["status"] = details.status
    if details.deadline is not None:
        updated_task_details["deadline"] = details.deadline
        _, deadline_prev, deadline_curr = Helpers.calculate_updated_deadline(
            details.deadline
        )
    if details.description is not None:
        updated_task_details["description"] = details.description

    updated_task_details["assignee_list"] = current_assignees
    updated_task_details["document_list"] = current_documents
    task_name_updated, case_id_updated = db_func.update_task(
        task_details=updated_task_details, lawyer_email=lawyer.email
    )
    role = lawyer.personnel_type.capitalize()

    if details.deadline is not None:
        Helpers.delete_notification(
            lawyer.email,
            "tasks",
            content=f"Task #{details.task_id} deadline is almost near",
        )
        Helpers.delete_notification(
            lawyer.email,
            "tasks",
            content=f"Task #{details.task_id} deadline is today",
        )
        Helpers.add_notification(
            receiver=lawyer.email,
            sender=lawyer.email,
            type="tasks",
            content=f"Task #{details.task_id} deadline is almost near",
            target_id={"task_id": details.task_id},
            one_time=True,
            created_at=deadline_prev,
        )
        Helpers.add_notification(
            receiver=lawyer.email,
            sender=lawyer.email,
            type="tasks",
            content=f"Task #{details.task_id} deadline is today",
            target_id={"task_id": details.task_id},
            one_time=True,
            created_at=deadline_curr,
        )
        scheduler.schedule_task(
            Helpers.send_task_deadline,
            run_date=deadline_prev,
            lawyer=lawyer,
            task_details={
                "task_id": details.task_id,
                "task_name": updated_task_details["name"],
                "task_description": updated_task_details["description"],
            },
            deadline_type="in 1 day",
        )
        scheduler.schedule_task(
            Helpers.send_task_deadline,
            run_date=deadline_curr,
            lawyer=lawyer,
            task_details={
                "task_id": details.task_id,
                "task_name": updated_task_details["name"],
                "task_description": updated_task_details["description"],
            },
            deadline_type="today",
        )

    db_func.add_recent_action(
        lawyer_email=lawyer.email,
        case_id=case_id_updated,
        action=f"has updated the {task_name_updated} task",
        actor=f"{lawyer.full_legal_name}",
        role=role,
    )

    for receiver in current_assignees:
        rec_lawyer = db_func.get_lawpersonnel(receiver)
        if rec_lawyer:
            Helpers.add_notification(
                receiver=rec_lawyer.email,
                sender=lawyer.email,
                type="tasks",
                content=f"{lawyer.full_legal_name} has updated a task",
                target_id={"task_id": details.task_id},
            )
            if details.deadline is not None:
                Helpers.delete_notification(
                    rec_lawyer.email,
                    "tasks",
                    content=f"Task #{details.task_id} deadline is almost near",
                )
                Helpers.delete_notification(
                    rec_lawyer.email,
                    "tasks",
                    content=f"Task #{details.task_id} deadline is today",
                )
                Helpers.add_notification(
                    receiver=rec_lawyer.email,
                    sender=lawyer.email,
                    type="tasks",
                    content=f"Task #{details.task_id} deadline is almost near",
                    target_id={"task_id": details.task_id},
                    one_time=True,
                    created_at=deadline_prev,
                )
                scheduler.schedule_task(
                    Helpers.send_task_deadline,
                    run_date=deadline_prev,
                    lawyer=rec_lawyer,
                    task_details={
                        "task_id": details.task_id,
                        "task_name": updated_task_details["name"],
                        "task_description": updated_task_details["description"],
                    },
                    deadline_type="in 1 day",
                )
                Helpers.add_notification(
                    receiver=rec_lawyer.email,
                    sender=lawyer.email,
                    type="tasks",
                    content=f"Task #{details.task_id} deadline is today",
                    target_id={"task_id": details.task_id},
                    one_time=True,
                    created_at=deadline_curr,
                )
                scheduler.schedule_task(
                    Helpers.send_task_deadline,
                    run_date=deadline_curr,
                    lawyer=rec_lawyer,
                    task_details={
                        "task_id": details.task_id,
                        "task_name": updated_task_details["name"],
                        "task_description": updated_task_details["description"],
                    },
                    deadline_type="today",
                )


class CaseTasksRetrievalInput(BaseModel):
    lawpersonnel_email: EmailStr
    case_id: LawyerCaseID


@app.post("/tasks/lawpersonnel/retrieve-case-tasks")
async def retrieve_case_tasks(payload: CaseTasksRetrievalInput):
    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    caseTasks = db_func.retrieve_case_specific_tasks(lawyer.email, payload.case_id)
    return JSONResponse(caseTasks)


@app.post("/tasks/lawpersonnel/retrieve-list")
async def retrieve_task_list(payload: CaseTasksRetrievalInput):
    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    all_tasks = db_func.retrieve_case_specific_tasks(lawyer.email, payload.case_id)
    allTasks = {}
    for task in all_tasks:
        assignees = task["assignee_list"]
        assignee_pp = []
        for assignee in assignees:
            user = db_func.get_lawpersonnel(assignee)
            if user:
                assignee_pp.append(user.profile_picture)
            else:
                assignee_pp.append("")
        task["assignee_profilePicUrls"] = assignee_pp
        allTasks[task["id"]] = task
    return JSONResponse(allTasks)
