from typing import Literal
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

    @staticmethod
    def send_signup_email(
        new_user_name: str,
        new_user_email: EmailStr,
        new_user_type: Literal["immigrant", "lawpersonnel"],
    ) -> None:
        # TODO: Connect to emailing service
        pass

    @staticmethod
    def send_verification_success(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_name: str,
        lawpersonnel_type: str,
    ) -> None:
        # profession = "Immigration Specialist"
        # if lawpersonnel_type not in ["lawstudent", "nonlawyer"]:
        #     profession = lawpersonnel_type.capitalize()
        # elif lawpersonnel_type == "lawstudent":
        #     profession = "Law Student"

        # button_url = f"{self.LAW_FRONTEND}dashboard"
        # body_text = f"""
        # Hello {lawpersonnel_name},

        # Congratulations! Your profile has been successfully verified as a {profession} on JustiGuide.

        # You can now:
        # • Connect with clients seeking immigration assistance
        # • Access all platform features
        # • Start managing immigration cases
        # • Receive and respond to client inquiries

        # Get started now by logging in to your dashboard:
        # {button_url}

        # Thank you for choosing JustiGuide to streamline your immigration practice.

        # Best regards,
        # The JustiGuide Team
        # """
        # title = "Your JustiGuide Profile is Verified"
        # system_type = "verification"
        # button_text = "Go to Dashboard"
        # text_list = [
        #     "Connect with clients seeking immigration assistance",
        #     "Access all platform features",
        #     "Start managing immigration cases",
        #     "Receive and respond to client inquiries",
        # ]
        # upper_body = f"<p>Congratulations! Your profile has been successfully verified as a <strong>{profession}</strong> on JustiGuide.</p>"
        # lower_body = "<p>Thank you for choosing JustiGuide to streamline your immigration practice.</p>"
        # body_html = self._generate_body_html(
        #     title=title,
        #     system_type=system_type,
        #     name=lawpersonnel_name,
        #     upper_body=upper_body,
        #     lower_body=lower_body,
        #     text_list=text_list,
        #     button_text=button_text,
        #     button_url=button_url,
        # )

        # try:
        #     self._send_email(
        #         receiver=lawpersonnel_email,
        #         subject=f"Congratulations! Your Profile is Verified",
        #         body_text=body_text,
        #         body_html=body_html,
        #     )
        # except ClientError as e:
        #     print(f"Error sending support request: {e.response['Error']['Message']}")
        # TODO: Connect to emailing service
        pass

    @staticmethod
    def send_verification_failure(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_name: str,
        failure_points: list[str] = None,
    ) -> None:

        # default_reasons = [
        #     "The submitted documentation was unclear or incomplete",
        #     "The information provided doesn't match our verification requirements",
        # ]
        # reasons = failure_points if failure_points else default_reasons

        # button_url = f"{self.LAW_FRONTEND}signup"
        # body_text = f"""
        # Hello {lawpersonnel_name},

        # We regret to inform you that we were unable to verify your profile on JustiGuide.

        # This could be due to one of the following reasons:
        # {'\n'.join([f"• {reason}" for reason in reasons])}

        # Please restart the verification process by visiting:
        # {button_url}

        # Thank you for choosing JustiGuide to streamline your immigration practice.

        # Best regards,
        # The JustiGuide Team
        # """
        # title = "Your JustiGuide Profile is Verified"
        # system_type = "verification"
        # button_text = "Restart Verification Process"
        # upper_body = f"""<p>We regret to inform you that we were unable to verify your profile on JustiGuide.</p><h3 style="color: #5080DE;">This could be due to one of the following reasons:</h3>"""
        # lower_body = "<p>Ensure that you provide clear, complete documentation and accurate information to facilitate the verification process.</p>"
        # body_html = self._generate_body_html(
        #     title=title,
        #     system_type=system_type,
        #     name=lawpersonnel_name,
        #     upper_body=upper_body,
        #     lower_body=lower_body,
        #     text_list=reasons,
        #     button_text=button_text,
        #     button_url=button_url,
        # )

        # try:
        #     self._send_email(
        #         receiver=lawpersonnel_email,
        #         subject=f"Profile Verification Status Update",
        #         body_text=body_text,
        #         body_html=body_html,
        #     )
        # except ClientError as e:
        #     print(f"Error sending support request: {e.response['Error']['Message']}")
        # TODO: Connect to emailing service
        pass
