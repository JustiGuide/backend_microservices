from typing import Literal
from fastapi import (
    APIRouter,
)
from pydantic import BaseModel, EmailStr
from helpers import Helpers
from authorization import CaseType
from .emailing_module import EmailService
from database import Functions

app = APIRouter()
db_func = Functions()
mailer = EmailService()

class PlainEmailInput(BaseModel):
    email_id: EmailStr

class SupportRequest(BaseModel):
    subject: str
    body: str
    email_id: EmailStr
    full_name: str = None

@app.post("/mailer/{user_type}/verify-email")
async def send_email_verification(payload: PlainEmailInput, user_type: Literal["immigrant", "lawpersonnel"]):
    code_value = mailer.send_email_verification(payload.email_id)
    db_func.add_user_verification(email=payload.email_id, verification_code=code_value)

@app.post("/mailer/{user_type}/request/{request_type}")
async def send_support_request(payload: SupportRequest, user_type: Literal["immigrant", "lawpersonnel"], request_type: Literal["support", "contact"]):
    is_support = request_type == "support"
    full_name = payload.full_name
    if is_support:
        user = db_func.get_immigrant(payload.email_id) or db_func.get_lawpersonnel(payload.email_id)
        if user:
            full_name = user.full_legal_name
        else:
            full_name = "JustiGuide User"
    mailer.send_support_request(
        subject=payload.subject,
        body=payload.body,
        email_id=payload.email_id,
        full_name=full_name,
        is_support=is_support,
    )

class ReferralEmail(BaseModel):
    referrer_name: str
    referrer_email: EmailStr
    referred_name: str
    referred_email: EmailStr

class ClientInvitation(BaseModel):
    lawpersonnel_name: str
    lawpersonnel_email: EmailStr
    client_name: str
    client_email: EmailStr
    case_type: CaseType

@app.post("/mailer/lawpersonnel/invite-client")
async def send_client_invitation(payload: ClientInvitation):
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    existing_clients = db_func.retrieve_clients(payload.lawpersonnel_email)
    invite_response = False
    if payload.client_email not in existing_clients:
        mailer.send_client_invitation(
            lawpersonnel_name=payload.lawpersonnel_name,
            lawpersonnel_email=payload.lawpersonnel_email,
            client_name=payload.client_name,
            client_email=payload.client_email,
        )
        invite_response = db_func.add_invitation(
            invited_type="invited_client",
            invited_email=payload.client_email,
            invitee_email=lawpersonnel.email,
            case_type=payload.case_type,
        )
        client = db_func.get_immigrant(payload.client_email)
        if client:
            Helpers.add_notification(
                receiver=client.email,
                sender=lawpersonnel.email,
                type="connection",
                content=f"{lawpersonnel.full_legal_name} has invited you as a client",
                target_id={},
            )
    return {"invite_success": invite_response}

@app.post("/mailer/immigrant/refer")
async def send_referral_email(payload: ReferralEmail):
    immigrant = db_func.get_immigrant(payload.referrer_email)
    referred = db_func.get_immigrant(payload.referred_email)
    if not referred:
        mailer.send_immigrant_referral(referred_name=payload.referred_name, referred_email=payload.referred_email, referrer_name=payload.referrer_name, referrer_email=payload.referrer_email)
        db_func.add_invitation(
            invited_type="refered_user",
            invitee_email=immigrant.email,
            invited_email=payload.referred_email,
        )

class PasswordReset(BaseModel):
    email_id: EmailStr
    pre_login: bool = True

@app.post("/mailer/{user_type}/reset-password")
async def initiate_password_reset(payload: PasswordReset, user_type: Literal["immigrant", "lawpersonnel"]):
    if payload.pre_login:
        requester = db_func.get_immigrant(payload.email_id) or db_func.get_lawpersonnel(payload.email_id)
        db_func.start_password_reset(email_id=payload.email_id, user_type=user_type)
        mailer.send_password_reset_email(requester_name=requester.full_legal_name, requester_email=payload.email_id, requester_type=user_type)

class CasePaymentNotice(BaseModel):
    lawpersonnel_name: str
    lawpersonnel_email: EmailStr
    immigrant_name: str
    checkout_id: str
    case_id: str


@app.post("/mailer/lawpersonnel/case-creation-notice")
async def send_case_payment_notice(payload: CasePaymentNotice):
    mailer.send_case_creation(lawpersonnel_name=payload.lawpersonnel_name,lawpersonnel_email=payload.lawpersonnel_email, immigrant_name=payload.immigrant_name, checkout_id=payload.checkout_id, case_id=payload.case_id)

class TaskDeadlineAlert(BaseModel):
    lawpersonnel_email: EmailStr
    lawpersonnel_name: str
    task_id: str
    task_name: str
    task_description: str
    deadline_type: Literal["in a day", "today"]


@app.post("/mailer/lawpersonnel/deadline-alert")
async def send_task_deadline_alert(payload: TaskDeadlineAlert):
    mailer.send_deadline_alert(
        lawpersonnel_email=payload.lawpersonnel_email,
        lawpersonnel_name=payload.lawpersonnel_name,
        task_id=payload.task_id,
        task_name=payload.task_name,
        task_description=payload.task_description,
        deadline_type=payload.deadline_type,
    )

class VerificationUpdate(BaseModel):
    lawpersonnel_email: EmailStr
    lawpersonnel_name: str
    lawpersonnel_type: str = None
    failure_points: list[str] = None

@app.post("/mailer/lawpersonnel/verification-{status}")
async def send_verification_update(payload: VerificationUpdate, status: Literal["success", "failure"]):
    if status == "success":
        mailer.send_verification_success(
            lawpersonnel_email=payload.lawpersonnel_email,
            lawpersonnel_name=payload.lawpersonnel_name,
            lawpersonnel_type=payload.lawpersonnel_type,
        )
    else:
        mailer.send_verification_failure(
            lawpersonnel_email=payload.lawpersonnel_email,
            lawpersonnel_name=payload.lawpersonnel_name,
            failure_points=payload.failure_points,
        )

class NewUserSignUp(BaseModel):
    full_name: str
    email_id: EmailStr

@app.post("/mailer/{user_type}/successful-signup")
async def send_successful_signup(payload: NewUserSignUp, user_type: Literal["immigrant", "lawpersonnel"]):
    mailer.send_signup_email(new_user_name=payload.full_name, new_user_email=payload.email_id, new_user_type=user_type)

class FormDeliveryNotice(BaseModel):
    sender_email: EmailStr
    sender_name: str
    letter_id: str
    form_name: str

@app.post("/mailer/{user_type}/form-delivery-notice")
async def send_form_delivery_notice(payload: FormDeliveryNotice):
    mailer.send_form_delivery_notification(sender_email=payload.sender_email, sender_name=payload.sender_name, letter_id=payload.letter_id, form_name=payload.form_name)

class ModuleGenNotice(BaseModel):
    immigrant_email: EmailStr
    immigrant_name: str


@app.post("/mailer/immigrant/{module}/generation-notice")
async def send_autofill_notice(payload: ModuleGenNotice, module: Literal["autofill", "recommendations"]):
    if module == "autofill":
        mailer.send_autofill_notification(immigrant_email=payload.immigrant_email, immigrant_name=payload.immigrant_name)
    else:
        mailer.send_lawyer_recommendation_notification(
            immigrant_email=payload.immigrant_email,
            immigrant_name=payload.immigrant_name,
        )

class SuccessfulPayment(BaseModel):
    email_id: EmailStr
    full_name: str
    price_paid: str

@app.post("/mailer/{user_type}/successful-payment-notice")
async def send_successful_payment_notice(payload: SuccessfulPayment, user_type: Literal["immigrant", "lawpersonnel"]):
    mailer.send_payment_success(email_id=payload.email_id, full_name=payload.full_name, price_paid=payload.price_paid, user_type=user_type)

class TeamMemberInvite(BaseModel):
    lawpersonnel_email: EmailStr
    lawpersonnel_name: str
    member_email: EmailStr
    member_name: str


@app.post("/mailer/lawpersonnel/team-invite")
async def send_teammember_invitation(payload: TeamMemberInvite):
    mailer.send_teammate_invitation(
        lawpersonnel_email=payload.lawpersonnel_email,
        lawpersonnel_name=payload.lawpersonnel_name,
        member_email=payload.member_email,
        member_name=payload.member_name,
    )

class ConnectionRequest(BaseModel):
    receiver_email: EmailStr
    receiver_name: str
    sender_name: str

@app.post("/mailer/lawpersonnel/connection-request")
async def send_connection_request(payload: ConnectionRequest):
    mailer.send_request_notification(receiver_email=payload.receiver_email, receiver_name=payload.receiver_name, sender_name=payload.sender_name)

class ExternalInvitation(BaseModel):
    lawpersonnel_email: EmailStr
    lawpersonnel_name: str
    immigrant_email: EmailStr
    immigrant_name: str

@app.post("/mailer/immigrant/external-invitation")
async def send_external_invitation(payload: ExternalInvitation):
    mailer.send_external_invitation(lawpersonnel_email=payload.lawpersonnel_email, lawpersonnel_name=payload.lawpersonnel_name, immigrant_email=payload.immigrant_email, immigrant_name=payload.immigrant_name)
