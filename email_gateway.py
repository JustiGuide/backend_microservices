from pydantic import EmailStr


class Email:
    @staticmethod
    def send_case_creation(self, lawpersonnel_name: str, lawpersonnel_email: EmailStr, immigrant_name: str, checkout_id: str, case_id: str) -> None:
        # button_url = f"{self.LAW_FRONTEND}case_payment/{case_id}/{checkout_id}"
        # body_text = f"""
        # Hello {lawpersonnel_name},

        # {immigrant_name} has signed the intake form. To start the case, please complete the case payment by clicking the link below:

        # {button_url}

        # Best regards,
        # The JustiGuide Team
        # """
        # title="Case Payment Required"
        # system_type="billing"
        # upper_body = f"<p><strong>{immigrant_name}</strong> signed the intake form. To start the case, please complete the case payment by clicking the button below:</p>"
        # button_text = "Complete Case Payment"
        # body_html = self._generate_body_html(title=title, system_type=system_type, name=immigrant_name, upper_body=upper_body, button_text=button_text, button_url=button_url)

        # try:
        #     self._send_email(
        #         receiver=lawpersonnel_email,
        #         subject=f"{immigrant_name} has signed the intake form",
        #         body_text=body_text,
        #         body_html=body_html,
        #         cc_receiver="info@justiguide.com",
        #     )
        # except ClientError as e:
        #     print(f"Error sending support request: {e.response['Error']['Message']}")
        # TODO: Connect to communications service
        pass