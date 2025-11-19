from typing import Literal
from fastapi import APIRouter, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from database import Functions
from authorization import PhoneNumber
from encryptor import Encrypt
from helpers import Helpers
from email_gateway import Email
from scheduler import TaskScheduler
from cleanup_gateway import DisconnectLawyer

scheduler = TaskScheduler()
disconnect_lawyer = DisconnectLawyer()
db_func = Functions()
app = APIRouter()

class ImmigrantLawyerConnection(BaseModel):
    immigrant_email: EmailStr
    lawpersonnel_email: EmailStr
    immigrant_number: PhoneNumber = None
    immigrant_address: str = None

@app.post("/connection/immigrant/accept-connection")
async def accept_lawpersonnel_invite(payload: ImmigrantLawyerConnection, background_tasks: BackgroundTasks):
    invited_lawyer_details = db_func.retrieve_invitation_data(invited_type="invited_client", invited_email=payload.immigrant_email)
    case_type = invited_lawyer_details[payload.lawpersonnel_email]
    case_id = db_func.check_existing_case(
        lawyer_email=payload.lawpersonnel_email,
        immigrant_email=payload.immigrant_email,
        case_type=case_type,
    )
    is_case = True
    if not case_id:
        is_case = False
        case_id = Encrypt.generate_uuid()

    db_func.update_connected_lawyers(
        immigrant_email=payload.immigrant_email,
        lawyer_email=payload.lawpersonnel_email,
        case_id=case_id,
    )
    if (
        invited_lawyer_details is not None
        and payload.lawpersonnel_email in invited_lawyer_details
        and not is_case
    ):
        client_number = payload.immigrant_number
        client_address = payload.immigrant_address
        client = db_func.get_immigrant(payload.immigrant_email)
        lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
        new_case_name = db_func.get_casename(case_type)
        description = f"New {new_case_name} Case for {client.full_legal_name}"
        case_name = f"{new_case_name} Case | {client.full_legal_name}"

        case_data = {
            "client_email": client.email,
            "client_number": client_number,
            "client_address": client_address,
            "case_name": case_name,
            "assignee_list": [],
            "description": description,
            "case_type": invited_lawyer_details[payload.lawpersonnel_email],
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
            Helpers.send_task_deadline,
            deadline_alertPrev,
            lawyer.email,
            f"{lawyer.full_legal_name}",
            intake_task_id,
            intake_task_details["name"],
            intake_task_details["description"],
            "in 1 day",
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
            Helpers.send_task_deadline,
            deadline_alertCurr,
            lawyer.email,
            f"{lawyer.full_legal_name}",
            intake_task_id,
            intake_task_details["name"],
            intake_task_details["description"],
            "today",
        )
        background_tasks.add_task(
            run_in_threadpool,
            Helpers.remove_invitation,
            invL_bool=True,
            pendCl_bool=False,
            invEL_bool=False,
            lawyer=lawyer,
            client=client,
            case_id=case_id,
        )
        db_func.add_tasks_to_case([intake_task_id], case_id)
        return {"lawyer": payload.lawpersonnel_email}


@app.post("/connection/immigrant/decline-connection")
async def accept_lawpersonnel_invite(
    payload: ImmigrantLawyerConnection, background_tasks: BackgroundTasks
):
    invited_client_details = db_func.retrieve_invitation_data(
        invited_type="invited_client", invited_email=payload.immigrant_email
    )
    client = db_func.get_immigrant(payload.immigrant_email)
    if invited_client_details and payload.lawpersonnel_email in invited_client_details:
        Helpers.add_notification(
            receiver=payload.lawpersonnel_email,
            sender=client.email,
            type="connection",
            content=f"{client.full_legal_name} declined your invite",
            target_id={},
            one_time=True,
        )
        background_tasks.add_task(
            run_in_threadpool, Helpers.remove_invited_client, payload.immigrant_email
        )

@app.post("/connection/immigrant/remove-connection")
async def remove_lawpersonnel_connection(payload: ImmigrantLawyerConnection):
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    disconnect_lawyer.disconnect_lawyer(lawyer.email, immigrant.email)
    return {"disconnection": True}


@app.post("/connection/immigrant/check-connection")
async def check_if_connection_pending(payload: ImmigrantLawyerConnection):
    all_connected = db_func.retrieve_connected_lawyers(immigrant_email=payload.immigrant_email, only_emails=True)
    pending_details = db_func.retrieve_invitation_data(
        invited_type="pending_client", invitee_email=payload.immigrant_email
    )
    retVal = {"pending": False, "connected": False}
    if pending_details is not None:
        if payload.lawpersonnel_email in pending_details:
            retVal["pending"] = True
        elif payload.lawpersonnel_email in all_connected:
            retVal["connected"] = True
            retVal["pending"] = False

    return JSONResponse(retVal)

@app.post("/connection/immigrant/save-lawyer")
async def save_lawyer(payload: ImmigrantLawyerConnection):
    db_func.save_lawyer(
        immigrant_email=payload.immigrant_email, lawyer_email=payload.lawpersonnel_email
    )


@app.post("/connection/immigrant/unsave-lawyer")
async def unsave_lawyer(payload: ImmigrantLawyerConnection):
    db_func.unsave_lawyer(
        immigrant_email=payload.immigrant_email, lawyer_email=payload.lawpersonnel_email
    )

class ConnectionRetrieval(BaseModel):
    immigrant_email: EmailStr

@app.post("/connection/immigrant/retrieve-connected-lawyers")
async def retrieve_connected_lawyers(payload: ConnectionRetrieval):
    all_connected_lawyers = db_func.retrieve_connected_lawyers(payload.immigrant_email)
    for lawyer in all_connected_lawyers:
        lawyer["case_ids"] = lawyer.pop("case_id")

    return JSONResponse(all_connected_lawyers)


@app.post("/connection/immigrant/check-connected-lawyers")
async def check_connected_lawyers(payload: ConnectionRetrieval):
    is_connected = db_func.check_if_connected_lawyers(payload.immigrant_email)
    return {"result": is_connected}

@app.post("/connection/immigrant/retrieve-saved-lawyers")
async def retrieve_saved_lawyers(payload: ConnectionRetrieval):
    all_saved_lawyers = [lawyer for lawyer in db_func.get_saved_lawyers(immigrant_email=payload.immigrant_email)]
    return JSONResponse(all_saved_lawyers)

class ClientInvitation(BaseModel):
    lawpersonnel_email: EmailStr
    client_email: EmailStr
    client_first_name: str
    client_last_name: str
    case_type: str

@app.post("/connection/lawpersonnel/send-connection-request")
async def send_client_connection_request(payload: ClientInvitation):
    existing_clients = db_func.retrieve_all_clients(lawpersonnel_email=payload.lawpersonnel_email)
    invite_response = False
    lawyer = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    if payload.client_email.lower() not in existing_clients:
        Email.send_client_invitation(lawpersonnel_name=lawyer.full_legal_name, lawpersonnel_email=payload.lawpersonnel_email, client_name=f"{payload.client_first_name} {payload.client_last_name}", client_email=payload.client_email)

        invite_response = db_func.add_invitation(
            invited_type="invited_client",
            invited_email=payload.client_email,
            invitee_email=lawyer.email,
            case_type=payload.case_type,
        )
        client = db_func.get_immigrant(payload.client_email)
        if client:
            Helpers.add_notification(
                receiver=client.email,
                sender=lawyer.email,
                type="connection",
                content=f"{lawyer.full_legal_name} has invited you as a client",
                target_id={},
            )
    return {"invite_success": invite_response}

class LawyerConnectionReq(BaseModel):
    lawpersonnel_email: EmailStr
    immigrant_email: EmailStr
    message: str
    immigrant_number: PhoneNumber
    immigrant_address: str
    case_type: str


@app.post("/connection/immigrant/send-connection-request")
async def send_lawpersonnel_connection_request(payload: LawyerConnectionReq):
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    external_lawyer = db_func.get_external_lawyer(payload.lawpersonnel_email)
    if external_lawyer:
        Email.send_external_invitation(lawpersonnel_email=external_lawyer.email, lawpersonnel_name=external_lawyer.fullName, immigrant_email=immigrant.email, immigrant_name=immigrant.full_legal_name)

    recipient = lawpersonnel or external_lawyer
    request_id = db_func.add_new_connection_request(message=payload.message, sender_email=payload.immigrant_email, recipient_email=recipient.email)
    if payload.immigrant_number != "" and payload.immigrant_address != "":
        if payload.immigrant_address.strip() == "":
            payload.immigrant_address = immigrant.location

        invited_type = "pending_client"
        if external_lawyer:
            invited_type = "invited_external_lawyer"

        db_func.add_invitation(
            invited_type=invited_type,
            invited_email=recipient.email,
            invitee_email=payload.immigrant_email,
            client_number=payload.immigrant_number,
            client_address=payload.immigrant_address,
            case_type=payload.case_type,
        )
        db_func.remove_lawyer_from_recommendations(
            payload.immigrant_email, payload.lawpersonnel_email
        )
    return {"message": "Message Sent Successfully.", "message_id": request_id}

@app.get("/connection/retrieve-all-requests")
async def retrieve_all_conn_requests():
    all_requests = db_func.retrieve_all_connection_requests()
    return JSONResponse(all_requests)

class RequestID(BaseModel):
    request_id: str
    new_status: str = None

@app.post("/connection/retrieve-specific-request")
async def retrieve_specific_request(payload: RequestID):
    request = db_func.retrieve_specific_connection_request(connection_id=payload.request_id)
    if not request:
        return {"status_code": 404, "error": "Request Not Found"}

    immigrant = db_func.get_immigrant(request.sender_email)
    return {
        "id": request.id,
        "sender_name": immigrant.full_legal_name,
        "sender_picture": immigrant.profile_pic,
        "message": request.message,
        "date_sent": request.timestamp,
        "status": request.status,
        "date_status_change": request.status_changed if request.status_changed else ""
    }


@app.post("/connection/change-request-status")
async def change_request_status(payload: RequestID, background_tasks: BackgroundTasks):
    request = db_func.retrieve_specific_connection_request(
        connection_id=payload.request_id
    )
    if not request:
        return {"status_code": 404, "error": "Request Not Found"}

    updated_request = db_func.change_connection_request_status(connection_id=payload.request_id, new_status=payload.new_status)

    immigrant = db_func.get_immigrant(updated_request.sender_email)
    lawpersonnel = db_func.get_lawpersonnel(updated_request.recipient_email)

    if "approve" in payload.new_status.lower() and lawpersonnel and immigrant:
        client_number = ""
        client_address = ""
        case_type = "nonimmigrant_worker"
        pending_details = db_func.retrieve_invitation_data(
            invited_type="pending_client", invitee_email=updated_request.sender_email
        )
        ret_case_type = None
        invited_external_lawyer_details = db_func.retrieve_invitation_data(
            invited_type="invited_external_lawyer",
            invitee_email=updated_request.sender_email,
        )
        if lawpersonnel.email in pending_details:
            client_number = pending_details[lawpersonnel.email]["client_number"]
            client_address = pending_details[lawpersonnel.email]["client_address"]
            ret_case_type = pending_details[lawpersonnel.email]["case_type"]
        elif updated_request.recipient_email in invited_external_lawyer_details:
            client_number = invited_external_lawyer_details[
                updated_request.recipient_email
            ]["client_number"]
            client_address = invited_external_lawyer_details[
                updated_request.recipient_email
            ]["client_address"]
            ret_case_type = invited_external_lawyer_details[
                updated_request.recipient_email
            ]["case_type"]
        if ret_case_type is not None:
            case_type = ret_case_type
        is_case = db_func.check_existing_case(
            lawpersonnel.email, updated_request.sender_email, case_type
        )
        if not is_case:
            new_case_name = db_func.get_casename(case_type)
            description = f"New {new_case_name} Case for {immigrant.full_legal_name}"
            case_name = f"{new_case_name} Case | {immigrant.full_legal_name}"
            case_id = Encrypt.generate_uuid()
            db_func.update_connected_lawyers(
                immigrant_email=immigrant.email,
                lawyer_email=lawpersonnel.email,
                case_id=case_id,
            )
            case_data = {
                "client_email": immigrant.email,
                "client_number": client_number,
                "client_address": client_address,
                "case_name": case_name,
                "assignee_list": [],
                "description": description,
                "case_type": case_type,
                "case_id": case_id,
            }
            db_func.create_case(lawyer_email=lawpersonnel.email, case_details=case_data)

            intake_task_id = Encrypt.generate_uuid()

            intake_task_deadline_date, deadline_alertPrev, deadline_alertCurr = (
                Helpers.calculate_deadline(1)
            )
            intake_task_details = {
                "id": intake_task_id,
                "name": f"Send {immigrant.full_legal_name} Intake Form",
                "visibility": "all",
                "case_name": case_name,
                "case_id": case_id,
                "assignee_list": [],
                "status": "To-Do",
                "deadline": intake_task_deadline_date,
                "document_list": [],
                "description": f"Send the necessary Intake Form to {immigrant.full_legal_name}",
            }
            db_func.add_task(
                lawyer_email=lawpersonnel.email, task_details=intake_task_details
            )
            Helpers.add_notification(
                receiver=lawpersonnel.email,
                sender=lawpersonnel.email,
                type="tasks",
                content=f"Task #{intake_task_id} deadline is almost near",
                target_id={"task_id": intake_task_id},
                one_time=True,
                created_at=deadline_alertPrev,
            )
            scheduler.schedule_task(
                Helpers.send_task_deadline,
                deadline_alertPrev,
                lawpersonnel.email,
                f"{lawpersonnel.full_legal_name}",
                intake_task_id,
                intake_task_details["name"],
                intake_task_details["description"],
                "in 1 day",
            )
            Helpers.add_notification(
                receiver=lawpersonnel.email,
                sender=lawpersonnel.email,
                type="tasks",
                content=f"Task #{intake_task_id} deadline is today",
                target_id={"task_id": intake_task_id},
                one_time=True,
                created_at=deadline_alertCurr,
            )
            scheduler.schedule_task(
                Helpers.send_task_deadline,
                deadline_alertCurr,
                lawpersonnel.email,
                f"{lawpersonnel.full_legal_name}",
                intake_task_id,
                intake_task_details["name"],
                intake_task_details["description"],
                "today",
            )
            background_tasks.add_task(
                run_in_threadpool,
                Helpers.remove_invitation,
                invL_bool=False,
                pendCl_bool=True,
                invEL_bool=False,
                lawyer=lawpersonnel,
                client=immigrant,
                case_id=case_id,
            )
            db_func.add_tasks_to_case([intake_task_id], case_id)

    return updated_request

class UserRequests(BaseModel):
    immigrant_email: EmailStr = None
    lawpersonnel_email: EmailStr = None

@app.post("/connection/{user_type}/retrieve-requests")
async def retrieve_immigrant_sent_requests(payload: UserRequests, user_type: Literal["immigrant", "lawpersonnel"]):
    if user_type == "immigrant":
        all_sent = db_func.retrieve_all_sent_requests(sender_email=payload.immigrant_email)
        immigrant = db_func.get_immigrant(payload.immigrant_email)

        return [{
            "id": request.id,
            "sender_name": immigrant.full_legal_name,
            "sender_picture": immigrant.profile_pic,
            "message": request.message,
            "date_sent": request.timestamp,
            "status": request.status,
            "date_status_change": request.status_changed if request.status_changed else "",
        } for request in all_sent]
    else:
        all_received = db_func.retrieve_all_recieved_requests(recipient_email=payload.lawpersonnel_email)
        lawyer_requests = []
        for request in all_received:
            immigrant = db_func.get_immigrant(request.sender_email)
            lawyer_requests.append(
                {
                    "id": request.id,
                    "sender_name": immigrant.full_legal_name,
                    "sender_picture": immigrant.profile_pic,
                    "message": request.message,
                    "date_sent": request.timestamp,
                    "status": request.status,
                    "date_status_change": (
                        request.status_changed if request.status_changed else ""
                    ),
                }
            )
