from pydantic import EmailStr


class Email:
    @staticmethod
    def send_client_invitation(lawpersonnel_name: str, lawpersonnel_email: EmailStr, client_name: str, client_email: EmailStr) -> None:
        # body_text = f"""
        # Hello {client_name},

        # {lawpersonnel_name} has invited you to join JustiGuide, a platform designed to simplify your immigration application process.

        # With JustiGuide, you can:
        # • Easily communicate with your lawyer with the help of a multilingual AI agent
        # • Access and manage your case documents in one place
        # • Track your immigration application progress
        # • Receive updates and reminders for important dates

        # Get started with your immigration journey:
        # {self.IMMI_FRONTEND}

        # Best regards,
        # The JustiGuide Team
        # """
        # title="Welcome to JustiGuide: Your Immigrantion Application Partner"
        # system_type="invitation"
        # upper_body = f"""<p><strong>{lawpersonnel_name}</strong> has invited you to join JustiGuide, a platform designed to simplify your immigration application process.</p><h3 style="color: #5080DE;">With JustiGuide, you can:</h3>"""
        # text_list=[
        #     "Easily communicate with your lawyer with the help of a multilingual AI agent",
        #     "Access and manage your case documents in one place",
        #     "Track your immigration application progress",
        #     "Receive updates and reminders for important dates",
        # ]
        # button_text = "Get Started with JustiGuide"
        # button_url = self.IMMI_FRONTEND
        # body_html = self._generate_body_html(title=title, system_type=system_type, name=client_name, upper_body=upper_body, text_list=text_list, button_text=button_text, button_url=button_url)
        # try:
        #     self._send_email(
        #         receiver=client_email,
        #         subject=f"{lawpersonnel_name} has invited you",
        #         body_text=body_text,
        #         body_html=body_html,
        #         cc_receiver=lawpersonnel_email
        #     )
        # except ClientError as e:
        #     print(f"Error sending support request: {e.response['Error']['Message']}")
        # TODO: Connect to communication service
        pass

    @staticmethod
    def send_external_invitation(
        lawpersonnel_email: EmailStr,
        lawpersonnel_name: str,
        immigrant_email: EmailStr,
        immigrant_name: str,
    ) -> None:
        # button_url = self.LAW_FRONTEND
        # body_text = f"""
        # Hello {lawpersonnel_name},

        # {immigrant_name} has invited you to connect with them on JustiGuide, a legal tech platform for streamlining immigration application processes.

        # With JustiGuide, you can:
        # • Easily communicate with your client with the help of a multilingual AI agent
        # • Access and manage your case documents in one place
        # • Track your client's application progress
        # • Receive updates and reminders for important meetings regarding your client's application

        # PS: Kindly use this receiving address for the registration, which would reflect all your current connections awaiting your approval.

        # Get started with JustiGuide:
        # {button_url}

        # Best regards,
        # The JustiGuide Team
        # """
        # title = "Welcome to JustiGuide: Your Immigrantion Application Partner"
        # system_type = "connection"
        # upper_body = f"""<p><strong>{immigrant_name}</strong> has invited you to connect with them on JustiGuide, a legal tech platform for streamlining immigration application processes.</p><h3 style="color: #5080DE;">With JustiGuide, you can:</h3>"""
        # text_list = [
        #     "Easily communicate with your client with the help of a multilingual AI agent",
        #     "Access and manage your case documents in one place",
        #     "Track your client's application progress",
        #     "Receive updates and reminders for important meetings regarding your client's application",
        # ]
        # lower_body = f"""<p>PS: Kindly use this receiving address for the registration, which would reflect all your current connections awaiting your approval.</p>"""
        # button_text = "Get Started with JustiGuide"

        # body_html = self._generate_body_html(
        #     title=title,
        #     system_type=system_type,
        #     name=lawpersonnel_name,
        #     upper_body=upper_body,
        #     text_list=text_list,
        #     lower_body=lower_body,
        #     button_text=button_text,
        #     button_url=button_url,
        # )

        # try:
        #     self._send_email(
        #         receiver=lawpersonnel_email,
        #         subject=f"Connection Request",
        #         body_text=body_text,
        #         body_html=body_html,
        #         cc_receiver=immigrant_email,
        #     )
        # except ClientError as e:
        #     print(f"Error sending support request: {e.response['Error']['Message']}")
        # TODO: Connect with communication service
        pass

    def send_case_creation(
        self,
        lawpersonnel_name: str,
        lawpersonnel_email: EmailStr,
        immigrant_name: str,
        checkout_id: str,
        case_id: str,
    ) -> None:
        # button_url = f"{self.LAW_FRONTEND}case_payment/{case_id}/{checkout_id}"
        # body_text = f"""
        # Hello {lawpersonnel_name},

        # {immigrant_name} has signed the intake form. To start the case, please complete the case payment by clicking the link below:

        # {button_url}

        # Best regards,
        # The JustiGuide Team
        # """
        # title = "Case Payment Required"
        # system_type = "billing"
        # upper_body = f"<p><strong>{immigrant_name}</strong> signed the intake form. To start the case, please complete the case payment by clicking the button below:</p>"
        # button_text = "Complete Case Payment"
        # body_html = self._generate_body_html(
        #     title=title,
        #     system_type=system_type,
        #     name=immigrant_name,
        #     upper_body=upper_body,
        #     button_text=button_text,
        #     button_url=button_url,
        # )

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
        # TODO: Connect to communication service
        pass