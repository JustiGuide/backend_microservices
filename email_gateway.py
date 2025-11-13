from pydantic import EmailStr


class Email:

    @staticmethod
    def send_case_creation_email(lawpersonnel_email: EmailStr, client_email: EmailStr, checkout_id: str):
        # TODO: Connect with communications service
        pass

    @staticmethod
    def send_successful_payment_email(subscriber_email: EmailStr, price: str):
        # TODO: Connect with communications service
        pass