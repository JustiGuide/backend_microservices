from datetime import datetime
from typing import Literal
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from authorization import (
    Authorizer,
    SubCaseID,
    SubscriberEmail
)
from database import Functions
from stripe_gateway import Stripe
import stripe
from email_gateway import Email

db_func = Functions()
app = APIRouter()
stripe_module = Stripe()

class SubscriptionInput(BaseModel):
    subscriber_email: SubscriberEmail

@app.post("/sub/{user_type}/unsuccessful-case/{id}")
async def unsuccesful_case_payment(id: str, user_type: str=Literal["immigrant", "lawpersonnel"]):
    if user_type == "immigrant":
        immigrant = db_func.get_immigrant(id)
        if not immigrant:
            raise HTTPException(status_code=404, detail="Invalid Immigrant Username")
        db_func.remove_naturalization_entry(immigrant.email)
    else:
        case_id = Authorizer.subcase_id_validator(id)
        db_func.delete_lawyer_case_sub(case_id=case_id)

@app.post("/sub/{user_type}/successful-case/{id}")
async def succesful_case_payment(id: str, user_type: str=Literal["immigrant", "lawpersonnel"]):
    if user_type == "immigrant":
        immigrant = db_func.get_immigrant(id)
        checkout_id = db_func.retrieve_naturalization_checkout_id(immigrant.email)
        if stripe_module.retrieve_checkout_details(checkout_id, is_single=True):
            db_func.paid_naturalization(immigrant.email, checkout_id)
            stripe_sub_id = stripe_module.retrieve_checkout_details(checkout_id)
            price = stripe_module.retrieve_subscription_price(stripe_sub_id)
            Email.send_successful_payment_email(immigrant.email, price)
        else:
            return HTTPException(status_code=404, detail="Naturalization payment not received")

    else:
        case_id = Authorizer.subcase_id_validator(id)
        lawyer_case_sub = db_func.retrieve_lawyer_case_sub(case_id)
        if lawyer_case_sub != {}:
            checkout_id = lawyer_case_sub["case_checkout_id"]
            stripe_sub_id = stripe_module.retrieve_checkout_details(checkout_id)
            db_func.update_lawyer_case_sub(
                case_id=case_id, lawyer_email=lawyer_case_sub["lawyer_email"], case_sub_id=stripe_sub_id
            )
            db_func.start_case(lawyer_case_sub["lawyer_email"], case_id)
            price = stripe_module.retrieve_subscription_price(
                lawyer_case_sub["case_sub_id"]
            )
            Email.send_successful_payment_email(lawyer_case_sub["lawyer_email"], price)
        else:
            return HTTPException(status_code=404, detail="Case sub not found")


@app.post("/sub/{user_type}/retrieve-subscription")
async def retrieve_subscription(
    payload: SubscriptionInput, user_type: str = Literal["immigrant", "lawpersonnel"]
):
    sub_tier, _, sub_id = db_func.retrieve_subscription_details(
        user_email=payload.subscriber_email
    )
    price = None
    end_date = None
    if sub_id is not None:
        end_date = stripe_module.retrieve_subscription_end(sub_id)
        price = stripe_module.retrieve_subscription_price(
            sub_id, with_interval=True
        )

    return {"tier": sub_tier, "price": price, "end_date": end_date}


@app.post("/sub/{user_type}/retrieve-case")
async def retrieve_subscription(
    payload: SubscriptionInput, user_type: str = Literal["immigrant", "lawpersonnel"]
):
    sub_tier, _, sub_id = db_func.retrieve_subscription_details(
        user_email=payload.subscriber_email
    )
    price = None
    end_date = None
    if sub_id is not None:
        end_date = stripe_module.retrieve_subscription_end(sub_id)
        price = stripe_module.retrieve_subscription_price(sub_id, user_type != "immigrant")

    return {"tier": sub_tier, "price": price, "end_date": end_date}


@app.post("/sub/{user_type}/update-subscription")
async def update_subscription(
    payload: SubscriptionInput, user_type: str = Literal["immigrant", "lawpersonnel"]
):
    sub_tier, checkout_id, sub_id = db_func.retrieve_subscription_details(
        user_email=payload.subscriber_email
    )
    if checkout_id and sub_id:
        stripe_sub_id = stripe_module.retrieve_checkout_details(checkout_id)
        if stripe_sub_id:
            db_func.update_subscription_id(payload.subscriber_email, stripe_sub_id)
            db_func.update_user_subscription(user_type, payload.subscriber_email, sub_tier)
    else:
        return HTTPException(status_code=404, detail="No active subscription found.")


@app.post("/sub/{user_type}/cancel-subscription")
async def cancel_subscription(
    payload: SubscriptionInput,
    user_type: str = Literal["immigrant", "lawpersonnel"],
):
    sub_tier, _, sub_id = db_func.retrieve_subscription_details(
        user_email=payload.subscriber_email
    )
    if sub_tier != "free" and sub_id is not None:
        try:
            stripe.Subscription.cancel(sub_id)
        except:
            pass

    db_func.update_user_subscription(user_type=user_type, subscriber_email=payload.subscriber_email, subscription_type="free")
    db_func.update_subscription_details(user_email=payload.subscriber_email, sub_tier="free", checkout_id=None, sub_id=None)

@app.post("/sub/lawpersonnel/cancel-case/{case_id}")
async def cancel_case_payment(
    case_id: SubCaseID 
):
    case_sub = db_func.retrieve_lawyer_case_sub(case_id)
    if "case_sub_id" in case_sub and case_sub["case_sub_id"]:
        try:
            stripe.Subscription.cancel(case_sub["case_sub_id"])
        except:
            pass
    db_func.delete_lawyer_case_sub(case_id=case_id)
