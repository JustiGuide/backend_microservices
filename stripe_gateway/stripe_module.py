from datetime import datetime
import os
from typing import Literal, Union
from pydantic import EmailStr
import stripe
from dotenv import load_dotenv
from database import Functions

load_dotenv()

db_func = Functions()


class Stripe:
    publishableKey = os.getenv("publishableKey")
    secretKey = os.getenv("secretKey")
    immigrant_frontend = os.getenv("IMMI_FRONTEND")
    lawpersonnel_frontend = os.getenv("LAW_FRONTEND")
    payment_methods = ["card"]
    comprehensive_payment_methods = [
        "card",
        "cashapp",
        "link",
        "us_bank_account",
        "amazon_pay",
    ]
    case_debug_pids = {"one_time": "price_1R6fFOP6cNlgDSsm7yYP8xxi", "recurring": "price_1R6fGgP6cNlgDSsmuahuVf3m"}
    case_pids = {
        "nonimmigrant_worker": {
            "one_time": "price_1R71OKP6cNlgDSsmlmzLmDhh",
            "recurring": "price_1R71POP6cNlgDSsmkiudzyNO",
        },
        "employment_auth": {
            "one_time": "price_1R71PpP6cNlgDSsmtuTZFywx",
            "recurring": "price_1R71QOP6cNlgDSsmKZweEwA9",
        },
        "alien_rel": {
            "one_time": "price_1R71QtP6cNlgDSsmgoja8Rab",
            "recurring": "price_1R71RNP6cNlgDSsmkyLxZIb2",
        },
        "asylum_removal": {
            "one_time": "price_1R71RcP6cNlgDSsm0Yc6s43G",
            "recurring": "price_1R71RsP6cNlgDSsmDk8n4XPF",
        },
        "naturalization": {
            "one_time": "price_1RahWRP6cNlgDSsmL3uCPKNq"
        },
    }
    sub_debug_pid = "price_1PEabFP6cNlgDSsmwo4VLXmn"
    sub_pids = {
        "plus": {
            "monthly": "price_1QLEKPP6cNlgDSsmRuT9BnSs",
            "yearly": "price_1QLEO7P6cNlgDSsmFpsoslI1",
        },
        "nonlawyer": {
            "monthly": "price_1Qv37RP6cNlgDSsmm09DLrlV",
            "yearly": "price_1Qv37tP6cNlgDSsmoaftdTU6",
        },
        "lawyer": {
            "monthly": "price_1Qv39GP6cNlgDSsm6bq8QW79",
            "yearly": "price_1Qv39aP6cNlgDSsmd5yC7W3k",
        },
        "clinic": {
            "monthly": "price_1Qv3A3P6cNlgDSsmV6dHeZmk",
            "yearly": "price_1Qv3AQP6cNlgDSsmylGuAmOh",
        },
        "enterprise": {
            "monthly": "price_1QLDK4P6cNlgDSsmYpuuZcUf",
            "yearly": "price_1QLDK4P6cNlgDSsmYpuuZcUf",
        },
    }
    def __init__(self) -> None:
        stripe.api_key = self.secretKey
        self.tier = "free"
        self.email = "none"
        self.transaction_id = "none"
        self.sessID = "none"
        self.subID = "none"

    def get_case_pid(self, case_type: str, charge_type: str, debug: bool = False):
        if debug:
            return self.case_debug_pids[charge_type]
        return self.case_pids[case_type][charge_type]

    def get_subscription_pid(self, tier: str, duration: str, debug: bool = False):
        if debug:
            return self.sub_debug_pid
        return self.sub_pids[tier][duration]

    def create_subscription_session(self, tier: Literal["plus", "nonlawyer", "lawyer", "clinic", "enterprise", "pay"], duration: Literal["monthly", "yearly"], email: EmailStr, debug: bool = False, user:Literal["immigrant", "lawpersonnel"]="immigrant") -> str:
        sub_data = {
            "trial_settings": {"end_behavior": {"missing_payment_method": "pause"}},
            "trial_period_days": 3
        }
        mode = "subscription"
        if tier == "pay":
            sub_data = {}
            mode = "payment"
        domain = self.immigrant_frontend
        cancel = "error"
        if user != "immigrant":
            domain = self.lawpersonnel_frontend
            cancel = "failure"
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=self.comprehensive_payment_methods,
            line_items=[
                {
                    "price": self.get_subscription_pid(
                        tier=tier, duration=duration, debug=debug
                    ),
                    "quantity": 1,
                }
            ],
            subscription_data=sub_data,
            mode=mode,
            success_url=f"{domain}dashboard/profile/success",
            cancel_url=f"{domain}dashboard/profile/{cancel}"
        )
        return checkout_session.id

    def create_case_session(
        self,
        case_type: str = "naturalization",
        debug: bool = False,
        user: Literal["immigrant", "lawpersonnel"] = "immigrant"
    ):
        line_items = [
            {
                "price": self.get_case_pid(case_type=case_type, charge_type="one_time", debug=debug),
                "quantity": 1
            }
        ]
        mode="payment"
        subscription_data={}
        if case_type != "naturalization":
            mode="subscription"
            subscription_data = {
                "trial_settings": {"end_behavior": {"missing_payment_method": "pause"}},
                "trial_period_days": 30,
            }
            line_items.append(
                {
                    "price": self.get_case_pid(
                        case_type=case_type, charge_type="recurring", debug=debug
                    ),
                    "quantity": 1,
                }
            )
        domain = self.immigrant_frontend
        success = "n400_success"
        cancel = "n400_error"
        if user != "immigrant":
            domain = self.lawpersonnel_frontend
            success = "successful_casepayment"
            cancel = "unsuccessful_casepayment"

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=self.comprehensive_payment_methods,
            line_items=line_items,
            mode=mode,
            subscription_data=subscription_data,
            success_url=f"{domain}dashboard/profile/{success}",
            cancel_url=f"{domain}dashboard/profile/{cancel}",
        )
        return checkout_session.id

    def retrieve_checkout_details(self, checkout_id: str, is_single: bool = False) -> Union[str, bool]:
        session = stripe.checkout.Session.retrieve(checkout_id)
        if is_single:
            return session.payment_status
        if session.subscription:
            return session.subscription
        return None

    def retrieve_subscription_price(self, subscription_id: str, with_interval: bool = False) -> str:
        user_sub_details = stripe.Subscription.retrieve(subscription_id)
        stripe_sub = user_sub_details.items.data[-1]
        price_amount = f"{stripe_sub.plan.currency} {str((stripe_sub.plan.amount) / 100)}"
        if with_interval:
            interval = stripe_sub.plan.interval
            return f"{price_amount}/{interval}"
        return price_amount

    def retrieve_subscription_end(self, subscription_id: str) -> str:
        user_sub_details = stripe.Subscription.retrieve(subscription_id)
        end_date = datetime.fromtimestamp(user_sub_details.current_period_end)
        return end_date.strftime("%m/%d/%Y")