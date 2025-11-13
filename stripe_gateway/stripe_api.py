from typing import Literal
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, EmailStr
from authorization import (
    Authorizer,
    SubscriberEmail,
    SubscriptionTier,
    SubscriptionDuration,
    CaseType,
    LawyerCaseID
)
from database import Functions
from .stripe_module import Stripe
import stripe
from email_gateway import Email

db_func = Functions()
app = APIRouter()
stripe_module = Stripe()

class SubCheckoutSession(BaseModel):
    subscriber_email: SubscriberEmail
    tier: SubscriptionTier
    duration: SubscriptionDuration

class CaseCheckoutSession(BaseModel):
    case_type: CaseType
    subscriber_email: EmailStr
    case_id: LawyerCaseID = None
    client_email: EmailStr = None


@app.post("/stripe-webhook/")
# @app.post("/stripe/immigrant/webhook/")
# @app.post("/stripe/lawpersonnel/webhook/")
async def handle_stripe_webhook(
    request: Request, stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=stripe.api_key,
        )
    except ValueError as e:
        return HTTPException(status_code=404, detail=f"Invalid payload: {e}")
    except stripe.SignatureVerificationError as e:
        return HTTPException(status_code=404, detail=f"Invalid Signature: {e}")


@app.post("/stripe/{user_type}/create/sub-checkout")
async def create_sub_checkout(
    payload: SubCheckoutSession,
    user_type: str = Literal["immigrant", "lawpersonnel"]
):
    sub_tier, _, sub_id = db_func.retrieve_subscription_details(user_email=payload.subscriber_email)
    if sub_tier != "free" and sub_id is not None:
        try:
            stripe.Subscription.cancel(sub_id)
        except:
            pass

    subscription_case_id = stripe_module.create_subscription_session(payload.tier, payload.duration, user=user_type)
    db_func.update_checkout_id(user_email=payload.subscriber_email, checkout_id=subscription_case_id, sub_tier=payload.tier)
    return {"id": subscription_case_id}


@app.post("/stripe/{user_type}/create/case-checkout")
async def create_case_checkout(
    payload: CaseCheckoutSession,
    user_type: str = Literal["immigrant", "lawpersonnel"]
):
    case_checkout_id = stripe_module.create_case_session(payload.case_type, user=user_type)
    if user_type == "immigrant":
        db_func.update_naturalization_checkout_id(payload.subscriber_email, case_checkout_id)
    else:
        client_email = Authorizer.client_email_validator(
            payload.client_email, payload.subscriber_email
        )
        db_func.update_lawyer_case_sub(case_id=payload.case_id, lawyer_email=payload.subscriber_email, case_type=payload.case_type, client_email=client_email, case_checkout_id=case_checkout_id)

    return {"id": case_checkout_id}


@app.post("/stripe/{user_type}/regenerate/case-checkout/{id}")
async def regenerate_case_checkout(id: str, user_type: str=Literal["immigrant", "lawpersonnel"]):
    if user_type == "immigrant":
        immigrant = db_func.get_immigrant(id)
        if not immigrant:
            raise HTTPException(status_code=404, detail="Invalid Immigrant Username")
        db_func.remove_naturalization_entry(immigrant.email)
        case_checkout_id = stripe_module.create_case_session("naturalization", user=user_type)
        db_func.update_naturalization_checkout_id(immigrant.email, case_checkout_id)
    else:
        case_type, lawpersonnel_email, client_email = db_func.check_case(id)
        case_sub = db_func.retrieve_lawyer_case_sub(id)
        if case_sub != {}:
            case_type = case_sub.get("case_type")
            lawpersonnel_email = case_sub.get("lawyer_email")
            client_email = case_sub.get("client_email")

        if not case_type or not lawpersonnel_email or not client_email:
            raise HTTPException(status_code=404, detail="Case sub not found")

        case_checkout_id = stripe_module.create_case_session(case_type, user_type)
        db_func.update_lawyer_case_sub(
            case_id=id,
            lawyer_email=lawpersonnel_email,
            case_type=case_type,
            client_email=client_email,
            case_checkout_id=case_checkout_id
        )
        Email.send_case_creation_email(lawpersonnel_email=lawpersonnel_email, client_email=client_email, checkout_id=case_checkout_id)
