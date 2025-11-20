import os
from typing import Literal, Union
from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    Date,
    Float,
    String,
    Text,
    Boolean,
    create_engine
)
from encryptor import EncryptedBytes, EncryptedText, Encrypt
from datetime import date, datetime, timezone
load_dotenv()

Base = declarative_base()

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


class HandshakeDB(Base):
    __tablename__ = "user_handshake"
    uuid = Column(
        String(7), primary_key=True, nullable=False, default=Encrypt.generate_uuid
    )
    user_email = Column(EncryptedText, nullable=False)
    handshake_data = Column(EncryptedBytes, nullable=False)
    upload_date = Column(Date, nullable=False)
    last_used = Column(Date)
    upload_info = Column(EncryptedText, nullable=False)
    to_show = Column(Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "user_email": self.user_email,
            "handshake_data": self.handshake_data,
            "upload_date": self.upload_date,
            "last_used": self.last_used,
            "upload_info": self.upload_info,
            "to_show": self.to_show,
        }

    def __repr__(self):
        return f"<HandshakeDB(uuid={self.uuid}, user_email={self.user_email}, handshake_data={self.handshake_data}, upload_date={self.upload_date}, last_used={self.last_used}, upload_info={self.upload_info}, to_show={self.to_show})>"

class FormDetails(Base):
    __tablename__ = "form_details"
    uuid: str = Column(
        String(7), primary_key=True, nullable=False, default=Encrypt.generate_uuid
    )
    immigrant_email: EmailStr = Column(EncryptedText, nullable=False)
    form_name: str = Column(EncryptedText, nullable=False)
    form_details: dict = Column(EncryptedText, nullable=False)
    upload_date: date = Column(Date, nullable=False)
    allowed_lawyers: list[EmailStr] = Column(EncryptedText, nullable=True)

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "immigrant_email": self.immigrant_email,
            "form_name": self.form_name,
            "form_details": self.form_details,
            "upload_date": self.upload_date,
            "allowed_lawyers": self.upload_date
        }


class ImmigrantDocuments(Base):
    __tablename__ = "immigrant_documents"
    uuid: str = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    immigrant_email: EmailStr = Column(EncryptedText, nullable=False, index=True)
    file_url: str = Column(EncryptedText, nullable=False)
    file_type: str = Column(Text, nullable=False)

    def to_dict(self) -> dict[str, Union[str, EmailStr]]:
        return {
            "uuid": self.uuid,
            "immigrant_email": self.immigrant_email,
            "file_url": self.file_url,
            "file_type": self.file_type,
        }

    def __repr__(self) -> str:
        return f"<ImmigrantDocuments(uuid={self.uuid}, immigrant_email={self.immigrant_email}, file_url={self.file_url}, file_type={self.file_type})>"


class LawpersonnelDocuments(Base):
    __tablename__ = "lawpersonnel_documents"
    uuid: str = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    lawpersonnel_email: EmailStr = Column(EncryptedText, nullable=False, index=True)
    file_url: str = Column(EncryptedText, nullable=False)
    file_type: str = Column(Text, nullable=False)

    def to_dict(self) -> dict[str, Union[str, EmailStr]]:
        return {
            "uuid": self.uuid,
            "immigrant_email": self.lawpersonnel_email,
            "file_url": self.file_url,
            "file_type": self.file_type,
        }

    def __repr__(self) -> str:
        return f"<LawpersonnelDocuments(uuid={self.uuid}, immigrant_email={self.lawpersonnel_email}, file_url={self.file_url}, file_type={self.file_type})>"


class AllFiles(Base):
    __tablename__ = "all_files"
    uuid: str = Column(
        String(7), primary_key=True, nullable=False, default=Encrypt.generate_uuid
    )
    file_name: str = Column(EncryptedText, nullable=False)
    file_url: str = Column(EncryptedText, nullable=False)
    file_type: str = Column(EncryptedText, nullable=False)
    upload_date: datetime.date = Column(
        Date, nullable=False, default=datetime.now(tz=timezone.utc)
    )
    file_size: str = Column(String, nullable=False)
    open_read: bool = Column(Boolean, nullable=False, default=False)
    owner: EmailStr = Column(EncryptedText, nullable=False)
    owner_type: str = Column(EncryptedText, nullable=False)

    def to_dict(self) -> dict[str, Union[str, datetime.date, bool, EmailStr]]:
        return {
            "uuid": self.uuid,
            "file_name": self.file_name,
            "file_url": self.file_url,
            "file_type": self.file_type,
            "upload_date": self.upload_date,
            "file_size": self.file_size,
            "open_read": self.open_read,
            "owner": self.owner,
            "owner_type": self.owner_type,
        }

    def __repr__(self) -> str:
        return f"<AllFiles(uuid={self.uuid}, file_name={self.file_name}, file_url={self.file_url}, file_type={self.file_type}, upload_date={self.upload_date}, file_size={self.file_size}, open_read={self.open_read}, owner={self.owner}, owner_type={self.owner_type})>"

class CaseDocuments(Base):
    __tablename__ = "case_documents"
    uuid = Column(String(7), primary_key=True, default=Encrypt.generate_uuid)
    filename = Column(String(255), nullable=False)
    document_url = Column(EncryptedText, nullable=False)
    folder_name = Column(EncryptedText, nullable=False)
    lawyer_email = Column(EncryptedText, nullable=False, index=True)
    lawyer_case = Column(String(7), nullable=False)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "filename": self.filename,
            "document_url": self.document_url,
            "folder_name": self.folder_name,
            "lawyer_email": self.lawyer_email,
            "lawyer_case": self.lawyer_case
        }
    
    def __repr__(self):
        return f"<CaseDocuments(uuid={self.uuid}, filename={self.filename}, document_url={self.document_url}, folder_name={self.folder_name}, lawyer_email={self.lawyer_email}, lawyer_case={self.lawyer_case})>"


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

    def get_all_casetypes(self) -> (
        dict[str, dict[str, Union[str, list[dict[str, Union[str, int]]]]]]
    ):
        # TODO: Connect with case management service to get all case type (case_type.json)
        return {}

    def get_all_casename_slugs(self) -> list[str]:
        all_casetypes = self.get_all_casetypes()
        return [case for case in all_casetypes.keys()]

    def get_all_formnames(self) -> list[str]:
        all_casetypes = self.get_all_casetypes()
        return [case['form'] for case in all_casetypes.values()]

    def add_new_handshake(self, user_email: EmailStr, sign_bytes: bytes, upload_date: date, upload_info: dict[str, str]) -> None:
        db = self.Session()
        exist_sign = db.query(HandshakeDB).filter(HandshakeDB.user_email==user_email, HandshakeDB.handshake_data==sign_bytes).first()
        if not exist_sign:
            new_sign = HandshakeDB(
                user_email=user_email,
                handshake_data=sign_bytes,
                upload_date=upload_date,
                upload_info=upload_info,
            )
            db.add(new_sign)
            db.commit()
        db.close()

    def delete_sign(self, sign_id: str) -> bool:
        db = self.Session()
        sign = db.query(HandshakeDB).filter(HandshakeDB.uuid == sign_id).first()
        is_success = False
        if sign:
            sign.to_show = False
            db.commit()
            is_success = True
        db.close()
        return is_success

    def retrieve_every_sign(self):
        db = self.Session()
        signs = db.query(HandshakeDB).all()
        all_signs = [sign for sign in signs]
        db.close()
        return all_signs

    def retrieve_all_signs(self, user_email: EmailStr) -> list[HandshakeDB]:
        db = self.Session()
        signs = (
            db.query(HandshakeDB).filter(HandshakeDB.user_email == user_email).all()
        )
        all_signs = [sign for sign in signs]
        db.close()
        return all_signs

    def update_sign_date(self, sign_id: str, today_date: date) -> None:
        db = self.Session()
        if sign_id is not None:
            sign_entry = (
                db.query(HandshakeDB).filter(HandshakeDB.uuid == sign_id).first()
            )
            sign_entry.last_used = today_date
            db.commit()
            db.refresh(sign_entry)
        db.close()

    def retrieve_form_details(self, form_name: str, immigrant_email: EmailStr) -> dict:
        db = self.Session()
        form = db.query(FormDetails).filter(FormDetails.immigrant_email == immigrant_email, FormDetails.form_name == form_name).first()
        if not form:
            db.close()
            return "Form not found"
        form_details = form.form_details
        db.close()
        return form_details

    def add_form_details(self, form_name: str, immigrant_email: EmailStr, form_data: dict) -> None:
        db = self.Session()
        existing_form_data = (
            db.query(FormDetails)
            .filter(
                FormDetails.immigrant_email == immigrant_email,
                FormDetails.form_name == form_name,
            )
            .first()
        )
        if not existing_form_data:
            new_form_data = FormDetails(
                immigrant_email=immigrant_email,
                form_name=form_name,
                form_details=form_data,
                upload_date=datetime.now(timezone.utc),
            )
            db.add(new_form_data)
            db.commit()
        else:
            existing_form_data.form_details = form_data
            db.commit()
            db.refresh(existing_form_data)
        db.close()

    def retrieve_available_forms(self, immigrant_email: EmailStr, lawyer_email: EmailStr) -> dict:
        db = self.Session()
        available_forms = {}
        all_forms = (
            db.query(FormDetails)
            .filter(
                FormDetails.immigrant_email == immigrant_email
            )
            .all()
        )
        for form in all_forms:
            if lawyer_email in form.allowed_lawyers:
                available_forms[form.form_name] = form.form_details

        return available_forms

    def add_immigrant_filedetails(
        self,
        immigrant_email: EmailStr,
        file_url: str,
        file_type: Literal[
            "ai_chat_files", "forms", "personal_files", "filled_forms", "case_docs"
        ],
    ) -> None:
        db = self.Session()
        immigrant_file = ImmigrantDocuments(
            immigrant_email=immigrant_email.lower(),
            file_url=file_url,
            file_type=file_type,
        )
        db.add(immigrant_file)
        db.commit()
        db.close()
        pass

    def retrieve_filetype(self, user_email: EmailStr, file_url: str, user_type: Literal["immigrant", "lawpersonnel"]) -> str:
        db = self.Session()
        if user_type == "immigrant":
            immigrant_file = db.query(ImmigrantDocuments).filter(ImmigrantDocuments.immigrant_email==user_email.lower(), ImmigrantDocuments.file_url==file_url).first()
            if immigrant_file:
                db.close()
                return immigrant_file.file_type
        else:
            lawpersonnel_file = (
                db.query(LawpersonnelDocuments)
                .filter(
                    LawpersonnelDocuments.lawpersonnel_email == user_email.lower(),
                    LawpersonnelDocuments.file_url == file_url,
                )
                .first()
            )
            if lawpersonnel_file:
                db.close()
                return lawpersonnel_file.file_type

    def retrieve_file(self, user_email: EmailStr, file_url: str, user_type: Literal["immigrant", "lawpersonnel"]) -> Union[ImmigrantDocuments, LawpersonnelDocuments]:
        db = self.Session()
        if user_type == "immigrant":
            immigrant_file = (
                db.query(ImmigrantDocuments)
                .filter(
                    ImmigrantDocuments.immigrant_email == user_email.lower(),
                    ImmigrantDocuments.file_url == file_url,
                )
                .first()
            )
            if immigrant_file:
                db.close()
                return immigrant_file
        else:
            lawpersonnel_file = (
                db.query(LawpersonnelDocuments)
                .filter(
                    LawpersonnelDocuments.lawpersonnel_email == user_email.lower(),
                    LawpersonnelDocuments.file_url == file_url,
                )
                .first()
            )
            if lawpersonnel_file:
                db.close()
                return lawpersonnel_file

    def add_lawpersonnel_filedetails(
        self,
        lawpersonnel_email: EmailStr,
        file_url: str,
        file_type: Literal["ai_chat_files", "forms", "personal_files", "filled_forms", "case_docs"],
    ) -> None:
        db = self.Session()
        lawpersonnel_file = LawpersonnelDocuments(
            lawpersonnel_email=lawpersonnel_email.lower(),
            file_url=file_url,
            file_type=file_type,
        )
        db.add(lawpersonnel_file)
        db.commit()
        db.close()
        pass

    def store_file(
        self,
        file_name: str,
        file_size: str,
        file_url: str,
        file_type: str,
        readable: bool,
        email_id: EmailStr,
    ) -> str:
        db = self.Session()
        user = self.get_immigrant(email_id)
        lawyer = self.get_lawpersonnel(email_id)
        if user:
            owner = email_id
            owner_type = "immigrant"
        elif lawyer:
            owner = email_id
            owner_type = lawyer.personnel_type
        else:
            return HTTPException(
                status_code=400,
                detail="User or Lawyer not found",
            )

        file_id = None
        exist_file = (
            db.query(AllFiles)
            .filter(AllFiles.file_url == file_url, AllFiles.owner == owner)
            .first()
        )
        if not exist_file:
            new_file = AllFiles(
                file_name=file_name,
                file_size=file_size,
                file_url=file_url,
                file_type=file_type,
                open_read=readable,
                owner=owner,
                owner_type=owner_type,
            )
            db.add(new_file)
            db.commit()
            db.refresh(new_file)
            file_id = new_file.uuid
        else:
            exist_file.file_name = file_name
            exist_file.file_size = file_size
            exist_file.file_type = file_type
            exist_file.owner_type = owner_type
            exist_file.open_read = readable
            file_id = exist_file.uuid
            db.commit()
        db.close()
        return file_id

    def retrieve_case_type(self, lawpersonnel_email: EmailStr, case_id: str) -> str:
        # TODO: Connect with Case Management Service
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
        # TODO: Connect with relationship management
        pass

    def add_recent_action(
        self, lawyer_email: EmailStr, case_id: str, action: str, actor: str, role: str
    ) -> None:
        # db = self.Session()
        # action_time = datetime.now(timezone.utc)
        # new_action = CaseRecentActions(
        #     lawyer_email=lawyer_email.lower(),
        #     lawyer_case=case_id,
        #     action=action,
        #     actor=actor,
        #     role=role,
        #     action_time=action_time,
        # )

        # db.add(new_action)
        # db.commit()
        # db.close()
        # TODO: Connect with case management
        pass

    def update_lawyer_stat(self, lawyer_email: EmailStr, stat_type: str) -> None:
        # db = self.Session()
        # today = date.today()
        # lawyer_stat = (
        #     db.query(LawyerStats)
        #     .filter(
        #         LawyerStats.lawyer_email == lawyer_email.lower(),
        #         LawyerStats.stat_type == stat_type,
        #         LawyerStats.stat_date == today,
        #     )
        #     .first()
        # )
        # if lawyer_stat:
        #     lawyer_stat.stat_val = lawyer_stat.stat_val + 1
        # else:
        #     lawyer_stat = LawyerStats(
        #         lawyer_email=lawyer_email.lower(),
        #         stat_date=today,
        #         stat_type=stat_type,
        #     )
        #     db.add(lawyer_stat)
        # db.commit()
        # db.close()
        # TODO: Connect with user management
        pass

    def update_form_submission(self, lawyer_email: EmailStr, case_id: str) -> None:
        # db = self.Session()
        # case = (
        #     db.query(AllCases)
        #     .filter(
        #         AllCases.lawyer_email == lawyer_email.lower(),
        #         AllCases.case_id == case_id,
        #     )
        #     .first()
        # )
        # if case:
        #     case.form_submitted = True
        #     db.commit()
        #     db.refresh(case)
        # db.close()
        # TODO: Connect with case management
        pass

    def retrieve_intake_form(
        self, intake_form_id: str
    ) -> tuple[Union[str, None], Union[str, None]]:
        # db = self.Session()
        # intake_form = (
        #     db.query(LawyerForms).filter(LawyerForms.uuid == intake_form_id).first()
        # )
        # form_url = None
        # form_name = None
        # form_owner = None
        # if intake_form:
        #     form_url = intake_form.form_url
        #     form_name = intake_form.form_name
        #     form_owner = intake_form.lawyer_email
        # db.close()
        # return form_url, form_name, form_owner
        # TODO: Connect with relationship management
        pass

    def add_case_document(
        self,
        lawyer_email: EmailStr,
        case_id: str,
        document_url: str,
        filename: str,
        folder_name: str,
    ) -> tuple[str, str, str]:
        doc_url = document_url.replace(" ", "+")
        db = self.Session()
        file_id = Encrypt.generate_uuid()
        exist_document = (
            db.query(CaseDocuments)
            .filter(
                CaseDocuments.lawyer_email == lawyer_email.lower(),
                CaseDocuments.lawyer_case == case_id,
                CaseDocuments.document_url == doc_url.lower(),
            )
            .all()
        )
        if not exist_document and (
            self.check_if_paid(case_id)
            or self.get_lawpersonnel(lawyer_email).username
            in ["codyfisher", "dlane", "drobertson", "ghawkins", "carter.elizabeth1965"]
        ):
            new_document = CaseDocuments(
                uuid=file_id,
                filename=filename,
                document_url=doc_url,
                folder_name=folder_name,
                lawyer_email=lawyer_email.lower(),
                lawyer_case=case_id,
            )
            db.add(new_document)
            db.commit()
        db.close()
        return filename, doc_url, file_id

    def retrieve_folder_list(self, lawyer_email: EmailStr, case_id: str) -> list[str]:
        db = self.Session()
        documents = (
            db.query(CaseDocuments)
            .filter(
                CaseDocuments.lawyer_email == lawyer_email.lower(),
                CaseDocuments.lawyer_case == case_id,
            )
            .all()
        )
        result = []
        if documents and (
            self.check_if_paid(case_id)
            or self.get_lawpersonnel(lawyer_email).username
            in ["codyfisher", "dlane", "drobertson", "ghawkins", "carter.elizabeth1965"]
        ):
            for document in documents:
                result.append(document.folder_name)
        db.close()
        return result

    def retrieve_case_documents(
        self, lawyer_email: EmailStr, case_id: str, folder_name: str = None
    ) -> dict[str, dict[str, str]]:
        db = self.Session()
        documents = (
            db.query(CaseDocuments)
            .filter(
                CaseDocuments.lawyer_email == lawyer_email.lower(),
                CaseDocuments.lawyer_case == case_id,
            )
            .all()
        )
        if folder_name is not None:
            docs = [doc for doc in documents if doc.folder_name == folder_name]
        else:
            docs = [doc for doc in documents]
        # print(docs)
        result = {}
        if docs != [] and (
            self.check_if_paid(case_id)
            or self.get_lawpersonnel(lawyer_email).username
            in ["codyfisher", "dlane", "drobertson", "ghawkins", "carter.elizabeth1965"]
        ):
            for document in docs:
                result[document.uuid] = {
                    "name": document.filename,
                    "url": document.document_url.replace(" ", "+"),
                }

        db.close()
        return result

    def rename_document_folder(
        self,
        lawyer_email: EmailStr,
        case_id: str,
        old_folder_name: str,
        new_folder_name: str,
    ) -> None:
        db = self.Session()
        documents = (
            db.query(CaseDocuments)
            .filter(
                CaseDocuments.lawyer_email == lawyer_email.lower(),
                CaseDocuments.lawyer_case == case_id,
                CaseDocuments.folder_name == old_folder_name,
            )
            .all()
        )
        if documents and (
            self.check_if_paid(case_id)
            or self.get_lawpersonnel(lawyer_email).username
            in ["codyfisher", "dlane", "drobertson", "ghawkins", "carter.elizabeth1965"]
        ):
            for document in documents:
                old_url = document.document_url.split(
                    f'/{old_folder_name.replace(" ", "+")}/'
                )
                new_url = f"/{new_folder_name.replace(' ', '+')}/".join(old_url)
                document.folder_name = new_folder_name
                document.document_url = new_url
                db.commit()
                db.refresh(document)

        db.close()

    def change_document_folder(
        self,
        lawyer_email: EmailStr,
        case_id: str,
        document_uuid: str,
        new_folder_name: str,
    ) -> tuple[str, str]:
        db = self.Session()
        document = (
            db.query(CaseDocuments)
            .filter(
                CaseDocuments.lawyer_email == lawyer_email.lower(),
                CaseDocuments.lawyer_case == case_id,
                CaseDocuments.uuid == document_uuid,
            )
            .first()
        )
        if document and (
            self.check_if_paid(case_id)
            or self.get_lawpersonnel(lawyer_email).username
            in ["codyfisher", "dlane", "drobertson", "ghawkins", "carter.elizabeth1965"]
        ):
            old_folder_name = document.folder_name
            old_url = document.document_url.split(
                f'/{old_folder_name.replace(" ", "+")}/'
            )
            new_url = f"/{new_folder_name.replace(' ', '+')}/".join(old_url)
            document.folder_name = new_folder_name
            document.document_url = new_url
            db.commit()
            db.refresh(document)
            db.close()
            return old_folder_name, document.filename
        db.close()
        return None, None

    def delete_case_document(
        self, lawyer_email: EmailStr, case_id: str, document_uuid: str
    ) -> tuple[str, str]:
        db = self.Session()
        document = (
            db.query(CaseDocuments)
            .filter(
                CaseDocuments.lawyer_email == lawyer_email.lower(),
                CaseDocuments.lawyer_case == case_id,
                CaseDocuments.uuid == document_uuid,
            )
            .first()
        )
        filename = None
        document_url = None
        if document:
            filename = document.filename
            document_url = document.document_url
            db.delete(document)
            db.commit()
        db.close()
        return filename, document_url

    def delete_case_folder(
        self, lawyer_email: EmailStr, case_id: str, folder_name: str
    ) -> None:
        db = self.Session()
        documents = (
            db.query(CaseDocuments)
            .filter(
                CaseDocuments.lawyer_email == lawyer_email.lower(),
                CaseDocuments.lawyer_case == case_id,
                CaseDocuments.folder_name == folder_name,
            )
            .all()
        )
        if documents:
            for document in documents:
                db.delete(document)
            db.commit()
        db.close()

    def check_if_paid(self, case_id: str) -> bool:
        # case_sub = self.retrieve_lawyer_case_sub(case_id)
        # print(case_sub)
        # if case_sub != {} and case_sub["is_paid"]:
        #     return True
        # return False
        # TODO: connect with case management
        pass

    def retrieve_specific_case(
        self, lawyer_email: EmailStr, case_id: str
    ) -> tuple[list[EmailStr], EmailStr]:
        # db = self.Session()
        # case = (
        #     db.query(AllCases)
        #     .filter(
        #         AllCases.lawyer_email == lawyer_email.lower(),
        #         AllCases.case_id == case_id,
        #     )
        #     .first()
        # )
        # assignees = []
        # client_email = None
        # if case:
        #     assignees = case.assignee_list if case.assignee_list is not None else []
        #     client_email = case.client_email

        # db.close()
        # return assignees, client_email
        # TODO: Connect with case management
        pass

    def retrieve_used_storage(self, email_id: EmailStr) -> int:
        db = self.Session()
        used_storage = 0
        all_files = db.query(AllFiles).filter(AllFiles.owner == email_id).all()
        if all_files:
            for file in all_files:
                used_storage += file.file_size
        db.close()
        return used_storage
