from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from database import Functions
from authorization import Authorizer, LawyerCaseID, PhoneNumber, CaseType, CaseStatus
from encryptor import Encrypt
from helpers import Helpers
from scheduler import TaskScheduler

db_func = Functions()
app = APIRouter()
scheduler = TaskScheduler()

class CaseRetrievalInput(BaseModel):
    lawpersonnel_username: str


class CaseCreationInput(BaseModel):
    lawpersonnel_email: EmailStr
    client_email: EmailStr = Depends(Authorizer.client_email_validator)
    client_contact: PhoneNumber = None
    client_address: str = None
    case_name: str = None
    case_type: CaseType
    description: str = None
    assignees: list[EmailStr] = Depends(Authorizer.lawyer_team_validator)


@app.post("/cases/lawpersonnel/retrieve")
async def retrieve_lawpersonnel_cases(
    payload: CaseRetrievalInput,
):

    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_username)
    case_list = db_func.retrieve_all_cases(lawyer.email)
    return JSONResponse(case_list)


@app.post("/cases/lawpersonnel/create")
async def create_lawpersonnel_cases(
    payload: CaseCreationInput,
    background_tasks: BackgroundTasks,
):
    case_id = Encrypt.generate_uuid()
    client = db_func.get_immigrant(payload.client_email)
    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    is_case = db_func.check_existing_case(
        lawyer.email, payload.client_email, payload.case_type
    )
    if client is not None and not is_case:
        assignees = []
        for assignee in payload.assignees:
            assignee_obj = db_func.get_lawpersonnel(assignee)
            if assignee_obj:
                name = f"{assignee_obj.full_legal_name}"
                db_func.add_case_teammate(
                    lawyer_email=lawyer.email,
                    case_id=case_id,
                    member_name=name,
                    member_email=assignee_obj.email,
                )
                Helpers.add_notification(
                    receiver=assignee_obj.email,
                    sender=lawyer.email,
                    type="cases",
                    content=f"{lawyer.full_legal_name} has added you to case #{case_id}",
                    target_id={"case_id": case_id},
                )
        assignees.append(assignee_obj.email)
        client_details = db_func.retrieve_client_details(
            lawyer.email, payload.client_email
        )
        if len(client_details) > 0:
            clientPN = client_details["client_number"]
            clientAdd = client_details["client_address"]
        else:
            clientPN = payload.client_contact if payload.client_contact else "NoNumber"
            clientAdd = (
                payload.client_address if payload.client_address else client.location
            )
        case_name = Helpers.get_case_name(payload.case_type)

        description = f"New {case_name} Case for {client.full_legal_name}"
        if payload.description and payload.description.strip() != "":
            description = payload.description

        case_name = f"{case_name} Case | {client.full_legal_name}"
        if payload.case_name and payload.case_name.strip() != "":
            case_name = payload.case_name

        db_func.update_connected_lawyers(
            immigrant_email=client.email, lawyer_email=lawyer.email, case_id=case_id
        )
        case_data = {
            "client_email": client.email,
            "client_number": clientPN,
            "client_address": clientAdd,
            "case_name": case_name,
            "assignee_list": assignees,
            "description": description,
            "case_type": payload.case_type,
            "case_id": case_id,
        }
        db_func.create_case(lawyer_email=lawyer.email, case_details=case_data)

        intake_task_id = Encrypt.generate_uuid()

        intake_task_deadline_date, deadline_alertPrev, deadline_alertCurr = (
            Helpers.calculate_deadline(1)
        )
        intake_task_details = {
            "id": intake_task_id,
            "name": f"Send {client.full_legal_name} Intake Form",
            "visibility": "all",
            "case_name": case_name,
            "case_id": case_id,
            "assignee_list": [],
            "status": "To-Do",
            "deadline": intake_task_deadline_date,
            "document_list": [],
            "description": f"Send the necessary Intake Form to {client.full_legal_name}",
        }
        db_func.add_task(lawyer_email=lawyer.email, task_details=intake_task_details)
        Helpers.add_notification(
            receiver=lawyer.email,
            sender=lawyer.email,
            type="tasks",
            content=f"Task #{intake_task_id} deadline is almost near",
            target_id={"task_id": intake_task_id},
            one_time=True,
            created_at=deadline_alertPrev,
        )
        scheduler.schedule_task(
            func=Helpers.send_task_deadline,
            run_date=deadline_alertPrev,
            lawyer=lawyer,
            task_details={
                "task_id": intake_task_id,
                "task_name": intake_task_details["name"],
                "task_description": intake_task_details["description"],
            },
            deadline_type="in 1 day",
        )
        Helpers.add_notification(
            receiver=lawyer.email,
            sender=lawyer.email,
            type="tasks",
            content=f"Task #{intake_task_id} deadline is today",
            target_id={"task_id": intake_task_id},
            one_time=True,
            created_at=deadline_alertCurr,
        )
        scheduler.schedule_task(
            func=Helpers.send_task_deadline,
            run_date=deadline_alertCurr,
            lawyer=lawyer,
            task_details={
                "task_id": intake_task_id,
                "task_name": intake_task_details["name"],
                "task_description": intake_task_details["description"]
            },
            deadline_type="today",
        )
        background_tasks.add_task(
            run_in_threadpool,
            Helpers.remove_invitation,
            invL_bool=False,
            pendCl_bool=False,
            invEL_bool=False,
            lawyer=lawyer,
            client=client,
            case_id=case_id,
        )
        db_func.add_tasks_to_case([intake_task_id], case_id)


class CaseStatusUpdateInput(BaseModel):
    lawpersonnel_email: EmailStr
    case_id: LawyerCaseID
    status: CaseStatus


@app.post("/cases/lawpersonnel/update-status")
async def update_case_status(
    payload: CaseStatusUpdateInput,
):

    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    case_list = db_func.get_closed_cases(lawyer.email)
    role = lawyer.personnel_type.capitalize()
    db_func.add_recent_action(
        lawyer.email,
        payload.case_id,
        action=f"has updated the case status to {payload.status}",
        actor=f"{lawyer.full_legal_name}",
        role=role,
    )
    rows = db_func.update_case_status(lawyer.email, payload.case_id, payload.status)
    if payload.status.lower() == "closed":
        db_func.update_lawyer_stat(lawyer.email, "submitted_appl")
        if db_func.modify_lawyer_case_sub(payload.case_id, to_cancel=True):
            rows = db_func.update_case_status(lawyer.email, payload.case_id, payload.status)
        else:
            return {"updated": False, "reason": "Unable to cancel case subscription"}
    else:
        if payload.case_id in case_list:
            if db_func.modify_lawyer_case_sub(payload.case_id, to_cancel=False):
                rows = db_func.update_case_status(
                    lawyer.email, payload.case_id, payload.status
                )
            else:
                return {"updated": False, "reason": "Old Closed Case"}
        else:
            rows = db_func.update_case_status(
                lawyer.email, payload.case_id, payload.status
            )
    assignee_list, _ = db_func.retrieve_specific_case(lawyer.email, payload.case_id)
    for receiver in assignee_list:
        rec_lawyer = db_func.get_lawpersonnel(receiver)
        Helpers.add_notification(
            receiver=rec_lawyer.email,
            sender=lawyer.email,
            type="cases",
            content=f"{lawyer.full_legal_name} updated case status to '{payload.status}'",
            target_id={"case_id": payload.case_id},
        )
    if rows == 1:
        return {"updated": True}
    else:
        return {"updated": False, "reason": "Unable to update case"}


class CaseDetailsUpdateInput(BaseModel):
    lawpersonnel_email: EmailStr
    case_id: LawyerCaseID
    case_name: str
    case_description: str


@app.post("/cases/lawpersonnel/update-details")
async def updCaseDets(
    payload: CaseDetailsUpdateInput,
):
    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    _ = db_func.update_case(
        lawyer_email=lawyer.email,
        case_id=payload.case_id,
        case_name=payload.case_name,
        case_description=payload.case_description,
    )
    role = lawyer.personnel_type.capitalize()
    db_func.add_recent_action(
        lawyer.email,
        payload.case_id,
        action="has updated the case",
        actor=f"{lawyer.full_legal_name}",
        role=role,
    )
    assignee_list, _ = db_func.retrieve_specific_case(lawyer.email, payload.case_id)
    for receiver in assignee_list:
        rec_lawyer = db_func.get_lawpersonnel(receiver)
        Helpers.add_notification(
            receiver=rec_lawyer.email,
            sender=lawyer.email,
            type="cases",
            content=f"{lawyer.full_legal_name} updated case #{payload.case_id}",
            target_id={"case_id": payload.case_id},
        )


@app.post("/cases/lawpersonnel/retrieve-closed")
async def getClosed(
    payload: CaseRetrievalInput,
):

    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_username)
    case_list = db_func.get_closed_cases(lawyer.email)
    for id in case_list:
        client_email = case_list[id]["client_email"]
        client = db_func.get_immigrant(client_email)
        client_dets = db_func.retrieve_client_details(lawyer.email, client.email)
        case_list[id]["client_contact"] = client_dets["client_number"]
        case_list[id]["client_address"] = client_dets["client_address"]
        case_list[id]["client_name"] = f"{client.full_legal_name}"
        case_list[id]["client_profilePic"] = client.profile_pic
        assignee_pp = []
        for assignee in case_list[id]["assignees"]:
            user = db_func.get_lawpersonnel(assignee)
            assignee_pp.append(user.profile_picture)
        case_list[id]["assignee_profilePics"] = assignee_pp
    return JSONResponse(case_list)


class RetrieveClientCaseInput(BaseModel):
    lawpersonnel_email: EmailStr
    client_email: EmailStr = Depends(Authorizer.client_email_validator)


@app.post("/cases/lawpersonnel/retrieve-client-case")
async def get_clientCase(
    payload: RetrieveClientCaseInput,
):
    client = db_func.get_immigrant(payload.client_email)
    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    clientCases = db_func.retrieve_client_cases(lawyer.email, client.email)
    return JSONResponse(clientCases)


class CaseAttributesInput(BaseModel):
    lawpersonnel_email: EmailStr
    case_id: LawyerCaseID


@app.post("/cases/lawpersonnel/delete-case")
async def del_case(
    payload: CaseAttributesInput,
):

    try:
        lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
        db_func.delete_case(lawyer.email, payload.case_id)
        return {"cleanup": True}
    except:
        return {"cleanup": False}

@app.post("/cases/lawpersonnel/retrieve-recent-actions")
async def getRecAct(
    payload: CaseAttributesInput,
):
    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    recent_actions = db_func.retrieve_recent_actions(lawyer.email, payload.case_id)
    return JSONResponse(recent_actions)


