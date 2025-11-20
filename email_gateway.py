from pydantic import EmailStr


class Email:

    @staticmethod
    def send_email_verification(email_id: EmailStr) -> str:
        # code_val = str(random.randint(1000, 9999))
        # body_text = f"""
        # Welcome to JustiGuide!

        # Please enter this code to verify your email address: {code_val}
        # This verification ensures the security of your account and helps us provide you with a seamless experience in managing your immigration application process.
        # If you didn't request this code, please ignore this email.

        # Best regards,
        # The JustiGuide Team
        # """
        # title = f"Welcome to JustiGuide!"
        # system_type = "authentication"
        # upper_body = "</p>Please enter this code to verify your email address</p>"
        # lower_body = "<p>This verification ensures the security of your account and helps us provide you with a seamless experience in managing your immigration application process.</p><p>If you didn't request this code, please ignore this email.</p>"
        # body_html = self._generate_body_html(
        #     title=title,
        #     system_type=system_type,
        #     upper_body=upper_body,
        #     lower_body=lower_body,
        #     code=code_val,
        # )
        # try:
        #     self._send_email(
        #         receiver=email_id,
        #         subject=f"Verify Your Email Address",
        #         body_text=body_text,
        #         body_html=body_html,
        #     )
        #     return code_val
        # except ClientError as e:
        #     print(f"Error sending support request: {e.response['Error']['Message']}")
        # TODO: Connect to emailing service
        pass