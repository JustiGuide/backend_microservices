import os
from typing import Literal
import boto3
from botocore.exceptions import ClientError
import random
from dotenv import load_dotenv
from pydantic import EmailStr

load_dotenv()


class EmailService:
    AWS_REGION = "us-east-2"
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_ID")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
    client = boto3.client(
        "ses",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )
    LAW_FRONTEND = os.getenv('LAW_FRONTEND')
    IMMI_FRONTEND = os.getenv('IMMI_FRONTEND')
    SENDER_EMAIL = "JustiGuide <info@justiguide.com>"
    SUPPORT_RECEIVER = "info@justiguide.com"
    SIGN_OFF = "<p>If you have any questions or need assistance, please contact our support team</p><p>Best Regards,<br>The JustiGuide Team</p>"
    def _footer(self, system_type: str) -> str:
        if not system_type:
            return ""
        return f"""
            <hr><p><em style="font-size: smaller;">This message was sent via the JustiGuide {system_type} system.</em></p>
        """
    def _header(self, title: str) -> str:
        if not title:
            return ""
        return f"""
            <h2 style="color: #5080DE; font-size: 24px; margin-top: 0; margin-bottom: 20px;">{title}</h2>
        """
    def _greeting(self, name: str) -> str:
        if not name:
            return ""
        return f"""
            <p>Hello {name},</p>
        """
    def _unordered_list(self, text_list: list[str]) -> str:
        if not text_list:
            return ""
        unordered_tabs = "".join([f"<li>{list_item}</li>" for list_item in text_list])
        return f"""
        <ul>
            {unordered_tabs}
        </ul>
        """
    def _subsection(self, text_dict: dict[str, str]) -> str:
        if not text_dict:
            return ""
        subsection_tabs = "".join([f'<p><strong style="color: #5080DE;">{key}:</strong> {item}</p' for key, item in text_dict.items()])
        return f"""
        <div style="display: flex; justify-content: center;">
            <div style="border: 1px solid #ddd; padding: 0px 15px; margin-bottom: 20px; border-radius: 15px; width: 85%;">
                {subsection_tabs}
            </div>
        </div>
        """
    def _code(self, code: str) -> str:
        if not code:
            return ""
        return f"""<div style="background-color: #e3e3e3; padding: 10px 15px; border-radius: 5px; font-size: 24px; font-weight: bold; display: inline-block;">{code}</div>"""
    def _button(self, button_url: str, button_text: str) -> str:
        if not button_url:
            return ""
        return f"""
        <div style="text-align: center; margin: 30px 0;">
            <a href="{button_url}" style="background-color: #5080DE; color: #FFFFFF; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">{button_text}</a>
        </div>
        """
    def _send_email(self, receiver: EmailStr, subject: str, body_text: str, body_html: str, cc_receiver: EmailStr = None) -> None:
        destination = {"ToAddresses": [receiver]}
        if cc_receiver:
            destination["CcAddresses"] = [cc_receiver]
        _ = self.client.send_email(
            Destination=destination,
            Message={
                "Body": {"Html": {"Data": body_html}, "Text": {"Data": body_text}},
                "Subject": {"Data": f"{subject} | JustiGuide"},
            },
            Source=self.SENDER_EMAIL,
        )
    def _generate_body_html(
        self,
        title,
        system_type,
        name=None,
        upper_body=None,
        lower_body=None,
        text_dict=None,
        text_list=None,
        code=None,
        button_url=None,
        button_text=None,
    ):
        return f"""
        <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            {self._header(title)}
            {self._greeting(name)}
            {upper_body}
            {self._subsection(text_dict)}
            {self._unordered_list(text_list)}
            {self._code(code)}
            {self._button(button_url, button_text)}
            {lower_body}
            {self.SIGN_OFF}
            {self._footer(system_type)}
            </body>
        </html>
        """

    def send_support_request(self, subject: str, body: str, email_id: EmailStr, full_name: str, is_support: bool = True) -> None:
        type_req = "Support" if is_support else "Contact"
        body_text = f"""
        {type_req} Request From: {full_name} <{email_id}>
        Subject: {subject}
        Message: {body}
        """
        title = f"{type_req} Request From: {full_name}"
        system_type='support'
        text_dict={
            "From": email_id,
            "Subject": subject,
            "Message": body
        }
        body_html = self._generate_body_html(title=title, system_type=system_type, text_dict=text_dict)
        try:
            self._send_email(
                receiver="info@justiguide.com",
                subject=f"{type_req} Request: {subject}",
                body_text=body_text,
                body_html=body_html,
                cc_receiver=email_id,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_email_verification(self, email_id: EmailStr) -> str:
        code_val = str(random.randint(1000, 9999))
        body_text = f"""
        Welcome to JustiGuide!

        Please enter this code to verify your email address: {code_val}
        This verification ensures the security of your account and helps us provide you with a seamless experience in managing your immigration application process.
        If you didn't request this code, please ignore this email.

        Best regards,
        The JustiGuide Team
        """
        title=f"Welcome to JustiGuide!"
        system_type="authentication"
        upper_body="</p>Please enter this code to verify your email address</p>"
        lower_body="<p>This verification ensures the security of your account and helps us provide you with a seamless experience in managing your immigration application process.</p><p>If you didn't request this code, please ignore this email.</p>"
        body_html = self._generate_body_html(
            title=title,
            system_type=system_type,
            upper_body=upper_body,
            lower_body=lower_body,
            code=code_val,
        )
        try:
            self._send_email(
                receiver=email_id,
                subject=f"Verify Your Email Address",
                body_text=body_text,
                body_html=body_html,
            )
            return code_val
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_client_invitation(self, lawpersonnel_name: str, lawpersonnel_email: EmailStr, client_name: str, client_email: EmailStr) -> None:
        body_text = f"""
        Hello {client_name},

        {lawpersonnel_name} has invited you to join JustiGuide, a platform designed to simplify your immigration application process.

        With JustiGuide, you can:
        • Easily communicate with your lawyer with the help of a multilingual AI agent
        • Access and manage your case documents in one place
        • Track your immigration application progress
        • Receive updates and reminders for important dates

        Get started with your immigration journey:
        {self.IMMI_FRONTEND}

        Best regards,
        The JustiGuide Team
        """
        title="Welcome to JustiGuide: Your Immigrantion Application Partner"
        system_type="invitation"
        upper_body = f"""<p><strong>{lawpersonnel_name}</strong> has invited you to join JustiGuide, a platform designed to simplify your immigration application process.</p><h3 style="color: #5080DE;">With JustiGuide, you can:</h3>"""
        text_list=[
            "Easily communicate with your lawyer with the help of a multilingual AI agent",
            "Access and manage your case documents in one place",
            "Track your immigration application progress",
            "Receive updates and reminders for important dates",
        ]
        button_text = "Get Started with JustiGuide"
        button_url = self.IMMI_FRONTEND
        body_html = self._generate_body_html(title=title, system_type=system_type, name=client_name, upper_body=upper_body, text_list=text_list, button_text=button_text, button_url=button_url)
        try:
            self._send_email(
                receiver=client_email,
                subject=f"{lawpersonnel_name} has invited you",
                body_text=body_text,
                body_html=body_html,
                cc_receiver=lawpersonnel_email
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_teammate_invitation(self, lawpersonnel_email: EmailStr, lawpersonnel_name: str, member_email: EmailStr, member_name: str) -> None:
        body_text = f"""
        Hello {member_name},

        {lawpersonnel_name} has invited you to join their team on JustiGuide, a legal tech platform for streamlining immigration application processes.

        To accept the invitation and join the team, please click the link below:
        {self.LAW_FRONTEND}

        Best regards,
        The JustiGuide Team
        """
        title=f"Join {lawpersonnel_name}'s Team"
        system_type="invitation"
        upper_body=f"<p><strong>{lawpersonnel_name}</strong> has invited you to join their team on JustiGuide, a legal tech platform for streamlining immigration application processes.</p>"
        button_url=self.LAW_FRONTEND
        button_text="Accept Invitation"
        body_html = self._generate_body_html(
            title=title,
            system_type=system_type,
            name=member_name,
            upper_body=upper_body,
            button_text=button_text,
            button_url=button_url,
        )
        try:
            self._send_email(
                receiver=member_email,
                subject=f"Join {lawpersonnel_name}'s Team",
                body_text=body_text,
                body_html=body_html,
                cc_receiver=lawpersonnel_email,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_immigrant_referral(self, referred_name: str, referred_email: EmailStr, referrer_name: str, referrer_email: EmailStr) -> None:
        body_text = f"""
        Hey {referred_name}!,

        {referrer_name} has invited you to join JustiGuide, an innovative legal tech platform designed to streamline the immigration application process.

        JustiGuide offers:
        • AI-driven assistance for complex immigration procedures
        • Efficient document management
        • Comprehensive case tracking
        • User-friendly interface for both lawyers and immigrants
        • Secure and compliant data handling

        Start simplifying your immigration journey today!

        Get started here: {self.IMMI_FRONTEND}

        Best regards,
        The JustiGuide Team
        """
        title="Simplify Immigration Processes"
        system_type="referral"
        upper_body=f"""<p><strong>{referred_name}</strong> believes JustiGuide can help streamline your immigration application process.</p><h3 style="color: #5080DE;">Why Choose JustiGuide?</h3>"""
        text_list = [
            "AI-driven assistance for complex immigration procedures",
            "Efficient document management",
            "Comprehensive case tracking",
            "User-friendly interface for both lawyers and immigrants",
            "Secure and compliant data handling",
        ]
        lower_body = "<p>Start simplifying your immigration journey today!</p>"
        button_text = "Get Started with JustiGuide"
        button_url = self.IMMI_FRONTEND
        body_html = self._generate_body_html(title=title, system_type=system_type, name=referred_name, upper_body=upper_body, text_list=text_list, lower_body=lower_body, button_text=button_text, button_url=button_url)

        try:
            self._send_email(
                receiver=referred_email,
                subject=f"{referrer_name} has invited you",
                body_text=body_text,
                body_html=body_html,
                cc_receiver=referrer_email,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_password_reset_email(self, requester_name: str, requester_email: EmailStr, requester_type: Literal["immigrant", "lawpersonnel"]):
        button_url = (
            f"{self.IMMI_FRONTEND}login/resetpassword"
            if requester_type == "immigrant"
            else f"{self.LAW_FRONTEND}login/resetpassword"
        )
        body_text = f"""
            Hello {requester_name},

            We received a request to reset your password for your JustiGuide account. To proceed with resetting your password, please click on the link below:

            {button_url}

            If you did not request a password reset, please ignore this email or contact our support team if you have any concerns.

            This link will expire in 24 hours for security reasons.

            Best regards,
            The JustiGuide Team
        """
        title="Security Alert: Password Reset Requested"
        system_type="authentication"
        upper_body="<p>We received a request to reset your password for your JustiGuide account. To proceed with resetting your password, please click on the link below:</p>"
        lower_body="<p>If you did not request a password reset, please ignore this email or contact our support team if you have any concerns.</p><p>This link will expire in 24 hours for security reasons.</p>"
        button_text="Reset Your Password"
        body_html = self._generate_body_html(
            title=title,
            system_type=system_type,
            name=requester_name,
            upper_body=upper_body,
            lower_body=lower_body,
            button_text=button_text,
            button_url=button_url,
        )
        try:
            self._send_email(
                receiver=requester_email,
                subject=f"Password Reset Request",
                body_text=body_text,
                body_html=body_html,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_request_notification(self, receiver_email: EmailStr, receiver_name: str, sender_name: str) -> None:
        button_url = f"{self.LAW_FRONTEND}dashboard/inbox"
        body_text = f"""
        Hello {receiver_name},
        
        You have received a new conenction request

        {sender_name} would like to connect with you. Click on the link to view the request:

        {button_url}

        Best regards,
        The JustiGuide Team
        """
        title="New Connection Request"
        system_type = "connection"
        upper_body=f"""<p style="margin-bottom: 15px;">You have received a new connection request</p><p style="margin-bottom: 25px;">{sender_name} would like to connect with you.</p>"""
        button_text="View Request"
        body_html = self._generate_body_html(
            title=title,
            system_type=system_type,
            name=receiver_name,
            upper_body=upper_body,
            button_text=button_text,
            button_url=button_url,
        )
        try:
            self._send_email(
                receiver=receiver_email,
                subject=f"Connection Request",
                body_text=body_text,
                body_html=body_html,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_external_invitation(self, lawpersonnel_email: EmailStr, lawpersonnel_name: str, immigrant_email: EmailStr, immigrant_name: str) -> None:
        button_url = self.LAW_FRONTEND
        body_text = f"""
        Hello {lawpersonnel_name},

        {immigrant_name} has invited you to connect with them on JustiGuide, a legal tech platform for streamlining immigration application processes.

        With JustiGuide, you can:
        • Easily communicate with your client with the help of a multilingual AI agent
        • Access and manage your case documents in one place
        • Track your client's application progress
        • Receive updates and reminders for important meetings regarding your client's application

        PS: Kindly use this receiving address for the registration, which would reflect all your current connections awaiting your approval.

        Get started with JustiGuide:
        {button_url}

        Best regards,
        The JustiGuide Team
        """
        title = "Welcome to JustiGuide: Your Immigrantion Application Partner"
        system_type="connection"
        upper_body = f"""<p><strong>{immigrant_name}</strong> has invited you to connect with them on JustiGuide, a legal tech platform for streamlining immigration application processes.</p><h3 style="color: #5080DE;">With JustiGuide, you can:</h3>"""
        text_list = [
            "Easily communicate with your client with the help of a multilingual AI agent",
            "Access and manage your case documents in one place",
            "Track your client's application progress",
            "Receive updates and reminders for important meetings regarding your client's application",
        ]
        lower_body = f"""<p>PS: Kindly use this receiving address for the registration, which would reflect all your current connections awaiting your approval.</p>"""
        button_text = "Get Started with JustiGuide"

        body_html = self._generate_body_html(title=title, system_type=system_type, name=lawpersonnel_name, upper_body=upper_body, text_list=text_list, lower_body=lower_body, button_text=button_text, button_url=button_url)

        try:
            self._send_email(
                receiver=lawpersonnel_email,
                subject=f"Connection Request",
                body_text=body_text,
                body_html=body_html,
                cc_receiver=immigrant_email
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_case_creation(self, lawpersonnel_name: str, lawpersonnel_email: EmailStr, immigrant_name: str, checkout_id: str, case_id: str) -> None:
        button_url = f"{self.LAW_FRONTEND}case_payment/{case_id}/{checkout_id}"
        body_text = f"""
        Hello {lawpersonnel_name},

        {immigrant_name} has signed the intake form. To start the case, please complete the case payment by clicking the link below:

        {button_url}

        Best regards,
        The JustiGuide Team
        """
        title="Case Payment Required"
        system_type="billing"
        upper_body = f"<p><strong>{immigrant_name}</strong> signed the intake form. To start the case, please complete the case payment by clicking the button below:</p>"
        button_text = "Complete Case Payment"
        body_html = self._generate_body_html(title=title, system_type=system_type, name=immigrant_name, upper_body=upper_body, button_text=button_text, button_url=button_url)

        try:
            self._send_email(
                receiver=lawpersonnel_email,
                subject=f"{immigrant_name} has signed the intake form",
                body_text=body_text,
                body_html=body_html,
                cc_receiver="info@justiguide.com",
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_deadline_alert(self, lawpersonnel_email: EmailStr, lawpersonnel_name: str, task_id: str, task_name: str, task_description: str, deadline_type: str) -> None:
        body_text = f"""
        Task Deadline Reminder

        Hello {lawpersonnel_name},

        This is a reminder that your task deadline is {deadline_type}.

        Task Details:
        - Task ID: {task_id}
        - Task Name: {task_name}
        - Description: {task_description}

        Please ensure that all necessary actions are completed on time.

        Best regards,
        The JustiGuide Team
        """
        title="Task Deadline Reminder"
        system_type="notification"
        upper_body = (
            f"""<p><This is a reminder that your task deadline is {deadline_type}./p>"""
        )
        lower_body = f"""<p>Please ensure that all necessary actions are completed on time.</p>"""
        text_dict={
            "Task ID": task_id,
            "Task Name": task_name,
            "Description": task_description
        }
        body_html = self._generate_body_html(title=title, system_type=system_type, name=lawpersonnel_name, upper_body=upper_body, lower_body=lower_body, text_dict=text_dict)

        try:
            self._send_email(
                receiver=lawpersonnel_email,
                subject=f"Task Deadline Reminder: {task_name} ({task_id})",
                body_text=body_text,
                body_html=body_html,
                cc_receiver="info@justiguide.com",
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_autofill_notification(self, immigrant_email: EmailStr, immigrant_name: str) -> None:
        button_url = f"{self.IMMI_FRONTEND}dashboard/form"
        button_text = "Review Your Form"
        body_text = f"""
        Hello {immigrant_name},

        This is to inform you that your autofill has been successfully generated.

        You can review your form here: {button_url}

        If you did not request this, please contact our support team.

        Best regards,
        The JustiGuide Team
        """
        title="Autofill Generated"
        system_type="autofill generation"
        upper_body = "<p>This is to inform you that your autofill has been successfully generated.</p>"
        body_html = self._generate_body_html(
            title=title,
            system_type=system_type,
            name=immigrant_name,
            upper_body=upper_body,
            button_text=button_text,
            button_url=button_url,
        )
        try:
            self._send_email(
                receiver=immigrant_email,
                subject=f"Autofill Generation Notification",
                body_text=body_text,
                body_html=body_html,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_lawyer_recommendation_notification(
        self, immigrant_email: EmailStr, immigrant_name: str
    ) -> None:
        button_url = f"{self.IMMI_FRONTEND}dashboard/lawyers"
        button_text = "Review Your Recommendations"
        body_text = f"""
        Hello {immigrant_name},

        This is to inform you that lawyer recommendations for you have been successfully generated.

        You can review your recommendations here: {button_url}

        If you did not request this, please contact our support team.

        Best regards,
        The JustiGuide Team
        """
        title = "Lawyer Recommendations Generated"
        system_type = "autofill generation"
        upper_body = "<p>This is to inform you that lawyer recommendations for you have been successfully generated.</p>"
        body_html = self._generate_body_html(
            title=title,
            system_type=system_type,
            name=immigrant_name,
            upper_body=upper_body,
            button_text=button_text,
            button_url=button_url,
        )
        try:
            self._send_email(
                receiver=immigrant_email,
                subject=f"Lawyer Recommendations Generation Notification",
                body_text=body_text,
                body_html=body_html,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_verification_success(self, lawpersonnel_email: EmailStr, lawpersonnel_name: str, lawpersonnel_type: str) -> None:
        profession = "Immigration Specialist"
        if lawpersonnel_type not in ["lawstudent", "nonlawyer"]:
            profession = lawpersonnel_type.capitalize()
        elif lawpersonnel_type == "lawstudent":
            profession = "Law Student"

        button_url = f"{self.LAW_FRONTEND}dashboard"
        body_text = f"""
        Hello {lawpersonnel_name},
        
        Congratulations! Your profile has been successfully verified as a {profession} on JustiGuide.
        
        You can now:
        • Connect with clients seeking immigration assistance
        • Access all platform features
        • Start managing immigration cases
        • Receive and respond to client inquiries
        
        Get started now by logging in to your dashboard:
        {button_url}
        
        Thank you for choosing JustiGuide to streamline your immigration practice.
        
        Best regards,
        The JustiGuide Team
        """
        title = "Your JustiGuide Profile is Verified"
        system_type = "verification"
        button_text = "Go to Dashboard"
        text_list = [
            "Connect with clients seeking immigration assistance",
            "Access all platform features",
            "Start managing immigration cases",
            "Receive and respond to client inquiries",
        ]
        upper_body = f"<p>Congratulations! Your profile has been successfully verified as a <strong>{profession}</strong> on JustiGuide.</p>"
        lower_body = "<p>Thank you for choosing JustiGuide to streamline your immigration practice.</p>"
        body_html = self._generate_body_html(title=title, system_type=system_type, name=lawpersonnel_name, upper_body=upper_body, lower_body=lower_body, text_list=text_list, button_text=button_text, button_url=button_url)

        try:
            self._send_email(
                receiver=lawpersonnel_email,
                subject=f"Congratulations! Your Profile is Verified",
                body_text=body_text,
                body_html=body_html,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_verification_failure(
        self,
        lawpersonnel_email: EmailStr,
        lawpersonnel_name: str,
        failure_points: list[str] = None,
    ) -> None:

        default_reasons = [
            "The submitted documentation was unclear or incomplete",
            "The information provided doesn't match our verification requirements"
        ]
        reasons = failure_points if failure_points else default_reasons

        button_url = f"{self.LAW_FRONTEND}signup"
        body_text = f"""
        Hello {lawpersonnel_name},
        
        We regret to inform you that we were unable to verify your profile on JustiGuide.
        
        This could be due to one of the following reasons:
        {'\n'.join([f"• {reason}" for reason in reasons])}
        
        Please restart the verification process by visiting:
        {button_url}
        
        Thank you for choosing JustiGuide to streamline your immigration practice.
        
        Best regards,
        The JustiGuide Team
        """
        title = "Your JustiGuide Profile is Verified"
        system_type = "verification"
        button_text = "Restart Verification Process"
        upper_body = f"""<p>We regret to inform you that we were unable to verify your profile on JustiGuide.</p><h3 style="color: #5080DE;">This could be due to one of the following reasons:</h3>"""
        lower_body = "<p>Ensure that you provide clear, complete documentation and accurate information to facilitate the verification process.</p>"
        body_html = self._generate_body_html(
            title=title,
            system_type=system_type,
            name=lawpersonnel_name,
            upper_body=upper_body,
            lower_body=lower_body,
            text_list=reasons,
            button_text=button_text,
            button_url=button_url,
        )

        try:
            self._send_email(
                receiver=lawpersonnel_email,
                subject=f"Profile Verification Status Update",
                body_text=body_text,
                body_html=body_html,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_signup_email(self, new_user_name: str, new_user_email: EmailStr, new_user_type: Literal["immigrant", "lawpersonnel"]) -> None:
        button_url = f"{self.IMMI_FRONTEND}dashboard" if new_user_type == "immigrant" else f"{self.LAW_FRONTEND}dashboard"
        connector_type = "lawyers" if new_user_type == "immigrant" else "clients"
        button_text = "Get Started"
        body_text = f"""
        Hello {new_user_name},

        Congratulations on successfully signing up!
        We are excited to have you on our platform. You can now connect with {connector_type} and access a variety of resources to assist you.
        
        Click on this link to get started: {button_url}

        If you have any questions, feel free to reach out to our support team.

        Best regards,
        The JustiGuide Team
        """
        title = "Welcome to JustiGuide: Your Immigrantion Application Partner"
        system_type="authentication"
        name=new_user_name
        upper_body = f"""
        <p style="margin-bottom: 15px;">Congratulations on successfully signing up!</p>
        <p style="margin-bottom: 25px;">We are excited to have you on our platform. You can now connect with {connector_type} and access a variety of resources to assist you.</p>
        """
        body_html = self._generate_body_html(
            title=title,
            system_type=system_type,
            name=new_user_name,
            upper_body=upper_body,
            button_text=button_text,
            button_url=button_url,
        )

        try:
            self._send_email(
                receiver=new_user_email,
                subject=f"Welcome!",
                body_text=body_text,
                body_html=body_html,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")

    def send_form_delivery_notification(self, sender_email: EmailStr, sender_name: str, letter_id: str, form_name: str) -> None:
        body_text = f"""
        Hello {sender_name},

        We are pleased to inform you that your Form N400 with ID: {letter_id} has been successfully delivered.

        If you have any questions, feel free to reach out to our support team.

        Best regards,
        The JustiGuide Team
        """
        title = f"Form {form_name.upper()} has been delivered"
        system_type = "form delivery"
        upper_body = f"""<p style="margin-bottom: 15px;">We are pleased to inform you that your Form {form_name.upper()} with ID: {letter_id} has been successfully delivered.</p>"""

        body_html = self._generate_body_html(
            title=title,
            system_type=system_type,
            name=sender_name,
            upper_body=upper_body,
        )

        try:
            self._send_email(
                receiver=sender_email,
                subject=f"Form {form_name.upper()} has been delivered",
                body_text=body_text,
                body_html=body_html,
            )
        except ClientError as e:
            print(f"Error sending support request: {e.response['Error']['Message']}")


    def send_payment_success(
        self,
        email_id: EmailStr,
        full_name: str,
        price_paid: str,
        user_type: Literal["immigrant", "lawpersonnel"],
    ) -> None:

        if user_type == "immigrant":
            payment_subject = "Form"
            dashboard_url = f"{self.IMMI_FRONTEND}dashboard/form"
            button_text = "View Your Form"
            upper_body = "<p>Your payment for the <strong>Form</strong> has been successfully processed.</p><p>You can now access your form and continue with your application.</p>"
            subject_line = "Your Form Payment was Successful"
            plain_upper = "Your payment for the Form has been successfully processed.\nYou can now access your form and continue with your application."
        else:
            payment_subject = "Case"
            dashboard_url = f"{self.LAW_FRONTEND}dashboard"
            button_text = "Go to Dashboard"
            upper_body = "<p>Your payment for the <strong>Case</strong> has been successfully processed.</p><p>The case is now active, and you can begin managing it from your dashboard.</p>"
            subject_line = "Your Case Payment was Successful"
            plain_upper = "Your payment for the Case has been successfully processed.\nThe case is now active, and you can begin managing it from your dashboard."

        title = "Payment Successful"
        system_type = "billing"
        text_dict = {"Amount Paid": price_paid}
        lower_body = "<p>Thank you for using JustiGuide.</p>"
        body_text = f"""
            Hello {full_name},

            {plain_upper}

            Amount Paid: {price_paid}

            You can access your dashboard here: {dashboard_url}

            {lower_body.replace("<p>", "").replace("</p>", "")}

            Best regards,
            The JustiGuide Team
            """

        body_html = self._generate_body_html(
            title=title,
            system_type=system_type,
            name=full_name,
            upper_body=upper_body,
            lower_body=lower_body,
            text_dict=text_dict,
            button_text=button_text,
            button_url=dashboard_url,
        )
        
        try:
            self._send_email(
                receiver=email_id,
                subject=subject_line,
                body_text=body_text,
                body_html=body_html,
            )
        except ClientError as e:
            print(f"Error sending payment success email: {e.response['Error']['Message']}")
