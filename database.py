import os
from typing import Union, Literal
from pydantic import EmailStr
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    Float,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    create_engine,
    func,
)

from encryptor import EncryptedText, Encrypt
from datetime import datetime, timezone, timedelta

load_dotenv()


Base = declarative_base()


class TwilioContext(Base):
    __tablename__ = "twilio_context"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    added_date = Column(Date, nullable=False, server_default=func.now())
    user_number = Column(EncryptedText, nullable=False, index=True)
    user_context = Column(EncryptedText, nullable=False)
    ai_context = Column(EncryptedText, nullable=False)
    contact_method = Column(Text, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "added_date": self.added_date,
            "user_number": self.user_number,
            "user_context": self.user_context,
            "ai_context": self.ai_context,
            "contact_method": self.contact_method,
        }

    def __repr__(self):
        return f"<TwilioContext(uuid={self.uuid}, added_date={self.added_date}, user_number={self.user_number}, user_context={self.user_context}, ai_context={self.ai_context}, contact_method={self.contact_method})>"


class TwilioInteractions(Base):
    __tablename__ = "twilio_interactions"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    added_date = Column(Date, nullable=False, server_default=func.now())
    user_number = Column(EncryptedText, nullable=False)
    contact_reason = Column(EncryptedText, nullable=False)
    contact_method = Column(Text, nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "added_date": self.added_date,
            "user_number": self.user_number,
            "contact_reason": self.contact_reason,
            "contact_method": self.contact_method,
        }

    def __repr__(self):
        return f"<TwilioInteractions(uuid={self.uuid}, added_date={self.added_date}, user_number={self.user_number}, contact_reason={self.contact_reason}, contact_method={self.contact_method})>"


class Immigrants(Base):
    __tablename__ = "immigrants"
    username: str = Column(EncryptedText, index=True, nullable=False, unique=True)
    email: EmailStr = Column(
        EncryptedText, primary_key=True, nullable=False, unique=True
    )
    first_name: str = Column(EncryptedText, nullable=False)
    last_name: str = Column(EncryptedText, nullable=True)
    full_legal_name: str = Column(EncryptedText, nullable=False)
    location: str = Column(EncryptedText, nullable=True)
    hashed_password: str = Column(String(128), nullable=True)
    subscription_type: str = Column(String(20), default="free", nullable=False)
    profile_pic: str = Column(Text, nullable=False)
    chat_limit: float = Column(Float, default=10.0, nullable=False)
    data_collection: bool = Column(Boolean, default=True, nullable=False)
    receive_emails: bool = Column(Boolean, default=True, nullable=False)
    contact_number: str = Column(EncryptedText, nullable=True)
    date_of_birth: str = Column(EncryptedText, nullable=True)
    receipt_number: str = Column(EncryptedText, nullable=True)

    def extract_data(self) -> dict[str, Union[str, EmailStr]]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "location": self.location,
        }


class LawPersonnel(Base):
    __tablename__ = "law_personnel"

    # General Personnel Fields
    email: EmailStr = Column(EncryptedText, nullable=False, primary_key=True)
    username: str = Column(EncryptedText, nullable=False)
    hashed_password: str = Column(String, nullable=False)
    firstName: str = Column(EncryptedText, nullable=False)
    lastName: str = Column(EncryptedText, nullable=True)
    full_legal_name: str = Column(EncryptedText, nullable=False)
    profile_picture: str = Column(
        EncryptedText,
        nullable=False,
        default="https://doloreschatbucket.s3.us-east-2.amazonaws.com/lawyer-connections/template-pp.png",
    )
    contact_number = Column(EncryptedText, nullable=False)
    date_of_birth: str = Column(EncryptedText, nullable=True)
    professional_address: str = Column(EncryptedText, nullable=False)
    personnel_type: str = Column(String, nullable=False)
    verified: bool = Column(Boolean, nullable=True, default=False)
    subscription_tier: str = Column(String, nullable=False, default="free")
    receive_emails: bool = Column(Boolean, nullable=False, default=False)
    authorize_verification: bool = Column(Boolean, nullable=False, default=False)
    consent_data_collection: bool = Column(Boolean, nullable=False, default=False)

    # Lawyer-Specific Fields
    law_firm_name: str = Column(EncryptedText, nullable=True)
    experience: str = Column(EncryptedText, nullable=True)
    specialty: str = Column(EncryptedText, nullable=True)

    # General Details Object containing additional information.
    details: dict = Column(EncryptedText, nullable=False)

    def extract_data(self) -> dict[str, Union[str, EmailStr]]:
        return {
            "email": self.email,
            "username": self.username,
            "firstName": self.firstName,
            "lastName": self.lastName,
            "profile_picture": self.profile_picture,
            "contact_number": self.contact_number,
            "date_of_birth": self.date_of_birth,
            "professional_address": self.professional_address,
            "personnel_type": self.personnel_type,
            "verified": self.verified,
            "subscription_tier": self.subscription_tier,
            "receive_emails": self.receive_emails,
            "authorize_verification": self.authorize_verification,
            "consent_data_collection": self.consent_data_collection,
            "law_firm_name": self.law_firm_name,
            "experience": self.experience,
            "specialty": self.specialty,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return f"<LawPersonnel(email={self.email}, username={self.username}, firstName={self.firstName}, lastName={self.lastName}, personnel_type={self.personnel_type})>"


class ExternalLawyer(Base):
    __tablename__ = "external_lawyers"
    firstName: str = Column(EncryptedText, nullable=False)
    lastName: str = Column(EncryptedText, nullable=False)
    fullName: str = Column(EncryptedText, nullable=False)
    username: str = Column(EncryptedText, primary_key=True, nullable=False)
    email: EmailStr = Column(EncryptedText, nullable=False)
    lawFirmName: str = Column(EncryptedText, nullable=True)
    expertise: str = Column(String, nullable=True)
    experience: str = Column(String, nullable=True)
    professionalAddress: str = Column(EncryptedText, nullable=True)
    contactNumber: str = Column(EncryptedText, nullable=True)
    profilePicture: str = Column(
        EncryptedText,
        nullable=False,
        default="https://doloreschatbucket.s3.us-east-2.amazonaws.com/lawyer-connections/template-pp.png",
    )

    def to_dict(self) -> dict[str, Union[str, EmailStr]]:
        return {
            "firstName": self.firstName,
            "lastName": self.lastName,
            "fullName": self.fullName,
            "username": self.username,
            "email": self.email,
            "lawFirmName": self.lawFirmName,
            "expertise": self.expertise,
            "experience": self.experience,
            "professionalAddress": self.professionalAddress,
            "contactNumber": self.contactNumber,
            "profilePicture": self.profilePicture,
        }

    def __repr__(self) -> str:
        return f"<ExternalLawyer(username={self.username}, fullName={self.fullName}, email={self.email})>"


class LiveChatMessage(Base):
    __tablename__ = "live_chat_messages"
    id: str = Column(
        String(7), primary_key=True, index=True, default=Encrypt.generate_uuid
    )
    message: str = Column(EncryptedText, nullable=False)
    sender_email: EmailStr = Column(EncryptedText, nullable=True)
    recipient_email: EmailStr = Column(EncryptedText, nullable=True)
    timestamp: datetime = Column(DateTime(timezone=True), default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "sender_email": self.sender_email,
            "recipient_email": self.recipient_email,
            "timestamp": self.timestamp,
        }

    def __repr__(self):
        return f"<LiveChatMessage(id={self.id}, sender_email={self.sender_email}, recipient_email={self.recipient_email})>"


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(String(7), primary_key=True, index=True, default=Encrypt.generate_uuid)
    message = Column(EncryptedText)
    starred = Column(Boolean, default=False)
    sender_email = Column(EncryptedText, nullable=True)
    recipient_email = Column(EncryptedText, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    read = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "sender_email": self.sender_email,
            "recipient_email": self.recipient_email,
            "starred": self.starred,
            "timestamp": self.timestamp,
            "read": self.read,
        }

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, sender_email={self.sender_email}, recipient_email={self.recipient_email}, starred={self.starred}, read={self.read})>"


class Connection:
    def __init__(self, database_actor="postgresql"):
        self.connection_string = f"""{database_actor}://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}"""
        self.engine = create_engine(self.connection_string)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )


class Functions:
    db = Connection()
    Session = db.SessionLocal

    def get_immigrant(self, parameter: Union[EmailStr, str]) -> Immigrants:
        # TODO: Connect with User Management
        # db = self.Session()
        # if "@" in parameter:
        #     user = (
        #         db.query(Immigrants)
        #         .filter(Immigrants.email == parameter.lower())
        #         .first()
        #     )
        # else:
        #     user = (
        #         db.query(Immigrants)
        #         .filter(Immigrants.username == parameter.lower())
        #         .first()
        #     )
        # db.close()
        # return user
        pass

    def get_lawpersonnel(self, parameter: Union[EmailStr, str]) -> LawPersonnel:
        # TODO: Connect with User Management
        # db = self.Session()
        # if "@" in parameter:
        #     lawpersonnel = (
        #         db.query(LawPersonnel)
        #         .filter(LawPersonnel.email == parameter.lower())
        #         .first()
        #     )
        # else:
        #     lawpersonnel = (
        #         db.query(LawPersonnel)
        #         .filter(LawPersonnel.username == parameter.lower())
        #         .first()
        #     )
        # db.close()
        # return lawpersonnel
        pass

    def get_external_lawyer(self, parameter: Union[EmailStr, str]) -> ExternalLawyer:
        # TODO: Connect with User Management
        pass

    def add_twilio_interaction(
        self,
        user_number: str,
        contact_reason: str,
        contact_method: str = Literal["call", "text", "whatsapp"],
    ) -> None:
        db = self.Session()
        new_interaction = TwilioInteractions(
            user_number=user_number,
            contact_reason=contact_reason,
            contact_method=contact_method,
        )
        db.add(new_interaction)
        db.commit()
        db.close()

    def update_twilio_context(
        self,
        user_number: str,
        user_context: str,
        ai_context: str,
        contact_method: str = Literal["call", "text", "whatsapp"],
    ) -> None:
        db = self.Session()
        today = datetime.now(timezone.utc)
        start_date = today - timedelta(days=7)
        twilio_context = (
            db.query(TwilioContext)
            .filter(
                TwilioContext.user_number == user_number,
                TwilioContext.contact_method == contact_method,
                TwilioContext.added_date >= start_date,
            )
            .order_by(TwilioContext.added_date.desc())
            .first()
        )
        if twilio_context:
            twilio_context.user_context = user_context
            twilio_context.ai_context = ai_context
            db.commit()
            db.refresh(twilio_context)
        else:
            new_twilio_context = TwilioContext(
                user_number=user_number,
                user_context=user_context,
                ai_context=ai_context,
                contact_method=contact_method,
            )
            db.add(new_twilio_context)
            db.commit()
        db.close()

    def retrieve_twilio_context(
        self,
        user_number: str,
        contact_method: str = Literal["call", "text", "whatsapp"],
    ) -> tuple[str, str]:
        db = self.Session()
        today = datetime.now(timezone.utc)
        start_date = today - timedelta(days=7)
        user_context = None
        ai_context = None
        twilio_context = (
            db.query(TwilioContext)
            .filter(
                TwilioContext.user_number == user_number,
                TwilioContext.contact_method == contact_method,
                TwilioContext.added_date >= start_date,
            )
            .order_by(TwilioContext.added_date.desc())
            .first()
        )
        if twilio_context:
            user_context = twilio_context.user_context
            ai_context = twilio_context.ai_context

        db.close()
        return user_context, ai_context

    def update_twilio_conversation(
        self,
        user_num: str,
        messages: list[str],
        comm_type: Literal["call", "text", "whatsapp"],
        user_input: str,
        user_context: str,
        answer: str,
        ai_context: str,
        method: Literal["call", "text", "whatsapp"],
    ) -> bool:
        # TODO: connect with ai agents
        pass

    def update_twilio_reason(
        self,
        user_num: str,
        messages: list[str],
        comm_type: str = Literal["call", "text", "whatsapp"],
    ) -> bool:
        # TODO: connect with ai agents
        pass

    def add_user_verification(self, email: EmailStr, verification_code: str) -> None:
        # db = self.Session()
        # exist_user = (
        #     db.query(UsersVerification)
        #     .filter(UsersVerification.email == email.lower())
        #     .first()
        # )
        # if exist_user:
        #     exist_user.verification_code = verification_code
        #     db.commit()
        # else:
        #     user_verification = UsersVerification(
        #         email=email.lower(), verification_code=verification_code
        #     )
        #     db.add(user_verification)
        #     db.commit()
        # db.close()
        # TODO: Connect with user management
        pass

    def add_invitation(
        self,
        invited_type: Literal[
            "invited_client",
            "pending_case",
            "pending_client",
            "invited_external_lawyer",
            "invited_to_case",
            "invited_to_team",
            "refered_user",
        ],
        invitee_email: EmailStr,
        invited_email: EmailStr,
        case_type: Literal[
            "nonimmigrant_worker",
            "employment_auth",
            "alien_rel",
            "asylum_removal",
            "naturalization",
        ] = None,
        client_number: str = None,
        client_address: str = None,
        case_id: str = None,
        member_role: Literal["lawyer", "paralegal", "nonlawyer", "lawstudent"] = None,
        member_permissions: Literal["Admin", "Commenter", "Viewer"] = None,
        case_name: str = None,
        case_description: str = None,
        assignees: list[EmailStr] = None,
    ) -> bool:
        # db = self.Session()
        # exist_invitation = (
        #     db.query(Invitations)
        #     .filter(
        #         Invitations.invited_email == invited_email.lower(),
        #         Invitations.invited_type == invited_type,
        #         Invitations.invitee_email == invitee_email,
        #     )
        #     .first()
        # )
        # invitation_map = {
        #     "invited_client": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         case_type=case_type,
        #     ),
        #     "pending_case": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         case_id=case_id,
        #         client_number=client_number,
        #         client_address=client_address,
        #         case_name=case_name,
        #         case_description=case_description,
        #         case_type=case_type,
        #         assignees=assignees,
        #     ),
        #     "pending_client": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         client_number=client_number,
        #         client_address=client_address,
        #         case_type=case_type,
        #     ),
        #     "invited_external_lawyer": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         client_number=client_number,
        #         client_address=client_address,
        #         case_type=case_type,
        #     ),
        #     "invited_to_case": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         member_role=member_role,
        #         member_permissions=member_permissions,
        #         case_id=case_id,
        #     ),
        #     "invited_to_team": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #         member_role=member_role,
        #         member_permissions=member_permissions,
        #     ),
        #     "refered_user": Invitations(
        #         invited_type=invited_type,
        #         invited_email=invited_email.lower(),
        #         invitee_email=invitee_email.lower(),
        #     ),
        # }
        # invite_success = False
        # if not exist_invitation:
        #     new_invitation = invitation_map[invited_type]
        #     db.add(new_invitation)
        #     db.commit()
        #     add_record_to_airtable(new_invitation)
        #     invite_success = True
        # db.close()
        # return invite_success
        # TODO: connect with relationship management
        pass

    def retrieve_clients(self, lawyer_email: EmailStr) -> list[EmailStr]:
        # db = self.Session()
        # all_clients = []
        # clients = (
        #     db.query(AllClients)
        #     .filter(AllClients.lawyer_email == lawyer_email.lower())
        #     .all()
        # )
        # for client in clients:
        #     all_clients.append(client.client_email)

        # db.close()
        # return all_clients
        # TODO: Connect with relationship management
        pass

    def start_password_reset(
        self, email_id: EmailStr, user_type: Literal["immigrant", "lawpersonnel"]
    ) -> bool:
        # TODO: Connect with user management
        pass

    def retrieve_connected_lawyers(
        self, immigrant_email: EmailStr, case_id: str = None, only_emails: bool = False
    ) -> list[dict[str, Union[str, bool, list[str]]]]:
        # db = self.Session()
        # lawyers = []
        # connected_lawyers = (
        #     db.query(ImmigrantLawyerConnection)
        #     .filter(
        #         ImmigrantLawyerConnection.immigrant_email == immigrant_email.lower(),
        #         ImmigrantLawyerConnection.connected_boolean == True,
        #     )
        #     .all()
        # )
        # if connected_lawyers:
        #     # print(f"Connected lawyers for {immigrant_email}: {len(connected_lawyers)}")
        #     for connected_lawyer in connected_lawyers:
        #         # print(f"Processing lawyer: {connected_lawyer.lawyer_email}")
        #         if connected_lawyer.lawyer_case_ids is not None:
        #             lawyer = self.get_lawpersonnel(connected_lawyer.lawyer_email)
        #             if lawyer:
        #                 lawyers.append(
        #                     {
        #                         "lawyer": lawyer.email,
        #                         "Point of Contact": f"{lawyer.full_legal_name}",
        #                         "Law Firm Name": getattr(lawyer, "law_firm_name", None),
        #                         "Experience": getattr(lawyer, "experience", None),
        #                         "Expertise": getattr(lawyer, "specialty", None),
        #                         "Main Office": getattr(
        #                             lawyer, "professional_address", None
        #                         ),
        #                         "Phone Number": getattr(lawyer, "contact_number", None),
        #                         "Image link": getattr(lawyer, "profile_picture", None),
        #                         "Email Address": getattr(lawyer, "email", None),
        #                         "Verified": (
        #                             getattr(lawyer, "verified", False)
        #                             if hasattr(lawyer, "verified")
        #                             else False
        #                         ),
        #                         "case_id": connected_lawyer.lawyer_case_ids,
        #                     }
        #                 )
        # if case_id is not None:
        #     db.close()
        #     result = [
        #         lawyer["lawyer"] for lawyer in lawyers if case_id in lawyer["case_id"]
        #     ]
        #     return result[0] if len(result) > 0 else None
        # elif only_emails:
        #     db.close()
        #     return [lawyer["lawyer"] for lawyer in lawyers]
        # else:
        #     db.close()
        #     return lawyers
        # TODO: Connect with relationship manager
        pass

    def add_new_live_chat(
        self, sender_email: EmailStr, recipient_email: EmailStr, message: str
    ) -> None:
        db = self.Session()
        new_chat_message = LiveChatMessage(
            sender_email=sender_email, recipient_email=recipient_email, message=message
        )
        db.add(new_chat_message)
        db.commit()
        db.close()

    def add_new_case_chat(
        self,
        sender_email: EmailStr,
        recipient_email: EmailStr,
        message: str,
        message_id: str,
        read_status: bool = False
    ) -> None:
        # Create New Message Record
        db = self.Session()
        chat_message = ChatMessage(
            sender_email=sender_email,
            recipient_email=recipient_email,
            message=message,
            id=message_id,
            read=read_status,
        )

        # Save Record
        db.add(chat_message)
        db.commit()
        db.close()

    def get_any_user(self, parameter: Union[str, EmailStr]) -> Union[Immigrants, LawPersonnel]:
        return self.get_immigrant(parameter) or self.get_lawpersonnel(parameter)

    def retrieve_live_chat_history(
        self, sender_username: str, recipient_username: str
    ) -> list[dict[str, Union[str, EmailStr, datetime]]]:
        db = self.Session()
        sender = self.get_any_user(sender_username)
        recipient = self.get_any_user(recipient_username)
        all_messages = db.query(LiveChatMessage).filter(((LiveChatMessage.sender_email == (sender.email)) & (LiveChatMessage.recipient_email == (recipient.email))) | ((LiveChatMessage.sender_email == (recipient.email)) & (LiveChatMessage.recipient_email == (sender.email)))).order_by(LiveChatMessage.timestamp).all()

        chat_history = []
        for message in all_messages:
            message_receiver = self.get_any_user(message.recipient_email)
            message_sender = self.get_any_user(message.sender_email)
            chat_history.append(
                {
                    "id": message.id,
                    "senderName": f"{message_sender.full_legal_name}",
                    "senderUsername": message_sender.username,
                    "senderProfilePicture": getattr(message_sender, "profile_pic", None) or getattr(message_sender, "profile_picture", None),
                    "recipientName": f"{message_receiver.full_legal_name}",
                    "recipientUsername": message_receiver.username,
                    "recipientProfilePicture": getattr(message_receiver, "profile_pic", None)
                    or getattr(message_receiver, "profile_picture", None),
                    "message": message.message,
                    "timestamp": message.timestamp,
                }
            )
        db.close()
        return chat_history

    def retrieve_case_chat_history(
        self, sender_username: str, recipient_username: str
    ) -> list[dict[str, Union[str, EmailStr, bool, datetime]]]:
        db = self.Session()
        sender = self.get_any_user(sender_username)
        recipient = self.get_any_user(recipient_username)
        all_messages = (
            db.query(ChatMessage)
            .filter(
                (
                    (ChatMessage.sender_email == (sender.email))
                    & (ChatMessage.recipient_email == (recipient.email))
                )
                | (
                    (ChatMessage.sender_email == (recipient.email))
                    & (ChatMessage.recipient_email == (sender.email))
                )
            )
            .order_by(ChatMessage.timestamp)
            .all()
        )
        chat_history = []
        for message in all_messages:
            message_receiver = self.get_any_user(message.recipient_email)
            message_sender = self.get_any_user(message.sender_email)
            chat_history.append(
                {
                    "id": message.id,
                    "senderName": f"{message_sender.full_legal_name}",
                    "senderUsername": message_sender.username,
                    "senderProfilePicture": getattr(message_sender, "profile_pic", None)
                    or getattr(message_sender, "profile_picture", None),
                    "recipientName": f"{message_receiver.full_legal_name}",
                    "recipientUsername": message_receiver.username,
                    "recipientProfilePicture": getattr(
                        message_receiver, "profile_pic", None
                    )
                    or getattr(message_receiver, "profile_picture", None),
                    "message": message.message,
                    "timestamp": message.timestamp,
                    "starred": message.starred,
                    "read": message.read,
                }
            )
        db.close()
        return chat_history

    def retrieve_specific_live_chat_message(self, message_id: str) -> LiveChatMessage:
        db = self.Session()
        live_message = db.query(LiveChatMessage).filter(LiveChatMessage.id == message_id).first()
        db.close()
        return live_message

    def retrieve_specific_case_chat_message(self, message_id: str) -> ChatMessage:
        db = self.Session()
        case_message = (
            db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
        )
        db.close()
        return case_message

    def star_case_chat_message(self, message_id: str, is_starred: bool = True) -> Union[dict[str, Union[str, int]], ChatMessage]:
        db = self.Session()
        case_message = (
            db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
        )
        if not case_message:
            return {"status_code": 404, "error": "Message Not Found."}
        
        case_message.starred = is_starred
        db.commit()
        db.refresh(case_message)
        db.close()
        return case_message

    def retrieve_notification_count(self, recipient_email: EmailStr, type: Literal["cases", "tasks", "connection", "kyc", "forms", "teams", "lawyer_chat", "intake", "case_payment"], sender_email: EmailStr):
        # db = self.Session()
        # notification = (
        #     db.query(NotificationAlerts)
        #     .filter(
        #         NotificationAlerts.receiver == email.lower(),
        #         NotificationAlerts.type == type,
        #         NotificationAlerts.sender == sender.lower(),
        #     )
        #     .first()
        # )
        # count = 0
        # notification_id = None
        # message_string = "a new message"
        # if notification:
        #     notification_id = notification.id
        #     if "a new message" in notification.content:
        #         count = 1
        #         message_string = " new messages"
        #     else:
        #         split_string = notification.content.split(" new messages")[0]
        #         message_string = " new messages"
        #         match = re.search(r"\d+", split_string)
        #         if match:
        #             count = int(match.group())
        # return count, message_string, notification_id
        # TODO: Connect with user managemebt
        pass
