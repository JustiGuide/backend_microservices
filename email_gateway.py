from pydantic import EmailStr


class Email:

    @staticmethod
    def send_form_delivery_notification(
        sender_email: EmailStr, sender_name: str, letter_id: str, form_name: str
    ) -> None:
        # body_text = f"""
        # Hello {sender_name},

        # We are pleased to inform you that your Form N400 with ID: {letter_id} has been successfully delivered.

        # If you have any questions, feel free to reach out to our support team.

        # Best regards,
        # The JustiGuide Team
        # """
        # title = f"Form {form_name.upper()} has been delivered"
        # system_type = "form delivery"
        # upper_body = f"""<p style="margin-bottom: 15px;">We are pleased to inform you that your Form {form_name.upper()} with ID: {letter_id} has been successfully delivered.</p>"""

        # body_html = self._generate_body_html(
        #     title=title,
        #     system_type=system_type,
        #     name=sender_name,
        #     upper_body=upper_body,
        # )

        # try:
        #     self._send_email(
        #         receiver=sender_email,
        #         subject=f"Form {form_name.upper()} has been delivered",
        #         body_text=body_text,
        #         body_html=body_html,
        #     )
        # except ClientError as e:
        #     print(f"Error sending support request: {e.response['Error']['Message']}")
        # TODO: Connect with email service
        pass