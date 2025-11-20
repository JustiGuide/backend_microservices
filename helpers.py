from datetime import datetime, timezone, timedelta, date, time
import io
import mimetypes
import os
from pathlib import Path
import re
import string
from typing import Union
from calendar import monthrange
from PIL import Image
from fastapi import UploadFile
from pydantic import BaseModel, EmailStr
import requests
from scheduler import TaskScheduler
from database import LawPersonnel, Functions
from authorization import Certificates, Experiences, PersonnelType
from documents_gateway import DummyFile, DocumentsGateway
from email_gateway import Email


db_func = Functions()
scheduler = TaskScheduler()
docs = DocumentsGateway()

class UploadFile_Dummy(BaseModel):
    size: int
    content_type: str


class Helpers:
    image_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        "webp",
        ".svg",
    ]
    def formatDate(self, date: datetime) -> str:
        today = datetime.now(timezone.utc).date()
        if date == today:
            return "Today"
        elif date == today - timedelta(days=1):
            return "Yesterday"
        else:
            return date.strftime("%m/%d/%y")

    def parse_data(
        self, data: dict[str, Union[date, str, int]]
    ) -> list[dict[str, Union[datetime, int]]]:
        parsed_data = []
        for entry in data:
            if isinstance(entry["date"], str):
                entry["date"] = datetime.strptime(entry["date"], "%m%d%Y")
            elif isinstance(entry["date"], date):
                entry["date"] = datetime.combine(entry["date"], time.min)
            stat = int(entry["stat"]) if entry["stat"] is not None else 0
            parsed_data.append({"date": entry["date"], "stat": stat})
        return parsed_data

    def reformat_yearly(self, data: dict[str, Union[date, str, int]]) -> dict[str, int]:
        parsed_data = self.parse_data(data)
        current_date = datetime.today()
        current_year = current_date.year
        current_month = current_date.month
        month_names = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        yearly_format = {}
        for idx, name in enumerate(month_names):
            month_num = idx + 1
            if month_num > current_month:
                yearly_format[name] = None
            else:
                total = sum(
                    entry["stat"]
                    for entry in parsed_data
                    if entry["date"].year == current_year
                    and entry["date"].month == month_num
                )
                yearly_format[name] = total
        return yearly_format

    def reformat_monthly(
        self, data: dict[str, Union[date, str, int]], alt: bool
    ) -> dict[str, int]:
        parsed_data = self.parse_data(data)
        current_date = datetime.today()
        current_year = current_date.year
        current_month = current_date.month
        total_days = monthrange(current_year, current_month)[1]
        monthly_format = {}
        if not alt:
            for day in range(1, total_days + 1):
                day_key = f"{day:02d}"
                day_date = datetime(current_year, current_month, day)
                if day_date > current_date:
                    monthly_format[day_key] = None
                else:
                    total = sum(
                        entry["stat"]
                        for entry in parsed_data
                        if entry["date"].date() == day_date.date()
                    )
                    monthly_format[day_key] = total
        else:
            first_day_of_month = datetime(current_year, current_month, 1)
            first_day_index = (first_day_of_month.weekday() + 1) % 7
            week_counter = 1
            day_cursor = 1
            if first_day_index != 0:
                week_end_day = min(total_days, 1 + (6 - first_day_index))
            else:
                week_end_day = min(total_days, day_cursor + 6)

            while day_cursor <= total_days:
                week_start = datetime(current_year, current_month, day_cursor)
                week_end = datetime(current_year, current_month, week_end_day)
                if week_start > current_date:
                    monthly_format[f"Week {week_counter:02d}"] = None
                elif week_end > current_date:
                    total_val = sum(
                        entry["stat"]
                        for entry in parsed_data
                        if week_start.date()
                        <= entry["date"].date()
                        <= current_date.date()
                    )
                    monthly_format[f"Week {week_counter:02d}"] = total_val
                else:
                    total_val = sum(
                        entry["stat"]
                        for entry in parsed_data
                        if week_start.date() <= entry["date"].date() <= week_end.date()
                    )
                    monthly_format[f"Week {week_counter:02d}"] = total_val

                week_counter += 1
                day_cursor = week_end_day + 1
                if day_cursor <= total_days:
                    week_end_day = min(total_days, day_cursor + 6)
        return monthly_format

    def reformat_weekly(
        self, data: dict[str, Union[date, str, int]], alt: bool
    ) -> dict[str, int]:
        parsed_data = self.parse_data(data)
        current_date = datetime.today()
        weekly_format = {}
        if not alt:
            for i in range(6, -1, -1):
                day_date = current_date - timedelta(days=i)
                key = f"Day {(7 - i):02d}"
                if day_date > current_date:
                    weekly_format[key] = None
                else:
                    total = sum(
                        entry["stat"]
                        for entry in parsed_data
                        if entry["date"].date() == day_date.date()
                    )
                    weekly_format[key] = total
        else:
            sunday_offset = (current_date.weekday() + 1) % 7
            start_of_week = current_date - timedelta(days=sunday_offset)
            for i in range(7):
                day_date = start_of_week + timedelta(days=i)
                day_name = day_date.strftime("%A")
                if day_date > current_date:
                    weekly_format[day_name] = None
                else:
                    total = sum(
                        entry["stat"]
                        for entry in parsed_data
                        if entry["date"].date() == day_date.date()
                    )
                    weekly_format[day_name] = total
        return weekly_format

    def reformat_data(
        self,
        data: dict[str, Union[date, str, int]],
        monthly_alt: bool = True,
        weekly_alt: bool = True,
    ) -> dict[str, dict[str, int]]:
        return {
            "Year": self.reformat_yearly(data),
            "Month": self.reformat_monthly(data, monthly_alt),
            "Week": self.reformat_weekly(data, weekly_alt),
        }

    @staticmethod
    def initiate_lawyer_recommendation(user_email: EmailStr):
        # TODO: Connect with ai agent
        pass

    @staticmethod
    def initiate_autofill_generation(user_username: str):
        # TODO: Connect with ai agent
        pass

    @staticmethod
    def initiate_rag_update(user_username: str):
        # TODO: Connect with RAG
        pass

    @staticmethod
    def store_file(
        file: Union[UploadFile, UploadFile_Dummy],
        file_url: str,
        email_id: EmailStr,
        filename: str,
        readable: bool = False,
    ) -> str:
        # TODO: Connect with Docs Service
        # def get_file_size(file_size: int) -> str:
        #     if file_size < 1024:
        #         return f"{file_size} B"
        #     elif file_size < 1024**2:
        #         return f"{file_size / 1024:.2f} KB"
        #     elif file_size < 1024**3:
        #         return f"{file_size / 1024**2:.2f} MB"
        #     else:
        #         return f"{file_size / 1024**3:.2f} GB"

        # def add_file(
        #     self,
        #     file_name: str,
        #     file_size: str,
        #     file_url: str,
        #     file_type: str,
        #     readable: bool,
        #     email_id: EmailStr,
        # ) -> str:
        #     db = self.Session()
        #     user = self.get_immigrant(email_id)
        #     lawyer = self.get_lawpersonnel(email_id)
        #     if user:
        #         owner = email_id
        #         owner_type = "user"
        #     elif lawyer:
        #         owner = email_id
        #         owner_type = lawyer.personnel_type
        #     else:
        #         return HTTPException(
        #             status_code=400,
        #             detail="User or Lawyer not found",
        #         )

        #     file_id = None
        #     exist_file = (
        #         db.query(AllFiles)
        #         .filter(AllFiles.file_url == file_url, AllFiles.owner == owner)
        #         .first()
        #     )
        #     if not exist_file:
        #         new_file = AllFiles(
        #             file_name=file_name,
        #             file_size=file_size,
        #             file_url=file_url,
        #             file_type=file_type,
        #             open_read=readable,
        #             owner=owner,
        #             owner_type=owner_type,
        #         )
        #         db.add(new_file)
        #         db.commit()
        #         db.refresh(new_file)
        #         file_id = new_file.uuid
        #     else:
        #         exist_file.file_name = file_name
        #         exist_file.file_size = file_size
        #         exist_file.file_type = file_type
        #         exist_file.owner_type = owner_type
        #         exist_file.open_read = readable
        #         file_id = exist_file.uuid
        #         db.commit()
        #     db.close()
        #     return file_id

        # file_id = db_func.add_file(
        #     file_name=filename,
        #     file_size=get_file_size(file.size),
        #     file_url=file_url,
        #     file_type=file.content_type,
        #     readable=readable,
        #     email_id=email_id,
        # )
        # return file_id
        return ""

    def create_dummy_upload(self, local_file_path: str) -> UploadFile_Dummy:
        if local_file_path.startswith("http"):
            response = requests.head(local_file_path, timeout=10)
            response.raise_for_status()
            file_size = int(response.headers.get("Content-Length"))
        else:
            file_size = os.path.getsize(local_file_path)
        content_type, _ = mimetypes.guess_type(local_file_path)
        local_file = UploadFile_Dummy(size=file_size, content_type=content_type)
        return local_file

    @staticmethod
    def get_boolean(bool_val: Union[str, int, bool]) -> bool:
        boolVal = None
        if isinstance(bool_val, str):
            try:
                boolVal = bool(int(bool_val))
            except:
                boolVal = bool(bool_val)
        if isinstance(bool_val, int):
            boolVal = bool(bool_val)
        if isinstance(bool_val, bool):
            boolVal = bool_val
        return boolVal

    def resize_thumbnail(
        image: Image.Image, resize: tuple[int, int]
    ) -> Image.Image:
        min_dimension = min(image.width, image.height)
        resize_factor = resize[0] / min_dimension
        new_width = int(image.width * resize_factor)
        new_height = int(image.height * resize_factor)
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        left = (resized_image.width - resize[0]) / 2
        top = (resized_image.height - resize[1]) / 2
        cropped_image = resized_image.crop(
            (left, top, left + resize[0], top + resize[1])
        )
        return cropped_image

    def sign_saving(
        upload_info: dict[str, str], sign_data: bytes, email: str
    ) -> None:
        sign_image = Image.open(io.BytesIO(sign_data))
        date_uploaded = datetime.now(tz=timezone.utc).date()
        # signer.push_sign(sign_image, email, date_uploaded, upload_info)
        # TODO: connect with formfiller service

    @staticmethod
    def get_legal_filename(filename: str) -> str:
        legal_chars = set(string.ascii_letters + string.digits + "._-")
        cleaned_filename = "".join(c for c in filename if c in legal_chars)
        cleaned_filename = re.sub(r"\.+", ".", cleaned_filename)
        cleaned_filename = cleaned_filename.strip(". ")
        if not cleaned_filename:
            cleaned_filename = "file"
        max_length = 255
        if len(cleaned_filename) > max_length:
            cleaned_filename = cleaned_filename[:max_length]
        return cleaned_filename

    @staticmethod
    def verify_lawpersonnel(lawpersonnel_username: str):
        # TODO: connect to agent service
        pass

    def update_lawyer_to_team(self, user: LawPersonnel):
        team_lawyers, case_lawyers = db_func.new_lawpersonnel_add_team_case(
            user.email, f"{user.full_legal_name}"
        )
        if len(team_lawyers) > 0:
            for lawyer in team_lawyers:
                db_func.add_notification(
                    receiver=lawyer.email,
                    sender=user.email,
                    type="teams",
                    content=f"{user.full_legal_name} has joined your team",
                    target_id={"team_member": user.email},
                    one_time=True,
                )
                db_func.add_notification(
                    receiver=user.email,
                    sender=lawyer.email,
                    type="teams",
                    content=f"{lawyer.full_legal_name} has added you to their team",
                    target_id={},
                )
        if len(case_lawyers) > 0:
            for case_dets in case_lawyers:
                db_func.add_notification(
                    receiver=user.email,
                    sender=case_dets["lawyer"].email,
                    type="cases",
                    content=f"{case_dets['lawyer'].full_legal_name} has added you to case #{case_dets['case_id']}",
                    target_id={"case_id": case_dets["case_id"]},
                )

    async def background_new_lawpersonnel(
        self,
        upload_info: dict[str, str],
        data_dict: dict[str, Union[str, EmailStr, bool, int, list[dict[str, str]]]],
        personnel_type: PersonnelType,
        experiences: Experiences,
        certificates: Certificates,
        certificate_documents: list[UploadFile],
        profile_picture: UploadFile,
        lawpersonnel_sign: UploadFile,
        government_id: UploadFile,
        professional_licenses: UploadFile,
        address_proofs: UploadFile,
    ) -> None:
        username = db_func.generate_lawpersonnel_username(data_dict["email"].lower())
        all_certificates = []
        all_experiences = []
        if personnel_type[:-1] != "lawyer":
            for ex in experiences:
                if ex["is_current"]:
                    data_dict["law_firm_name"] = ex["organization_name"]

            if isinstance(certificates, list) and len(certificates) > 0:
                certificate_docs = certificate_documents
                if not isinstance(certificate_documents, list):
                    certificate_docs = [certificate_documents]
                for i, certificate in enumerate(certificates):
                    cert_file = certificate_docs[i]
                    cert_url = None
                    if not cert_file.filename.endswith("blob"):
                        cert_data = await cert_file.read()
                        filename = (
                            f"{certificate['certificate_name']}_{cert_file.filename}"
                        )
                        destination_dir = f"{personnel_type}/{username}/certificates"
                        s3_key, upd_file_name = docs.crosscheck_existing(
                            destination_dir, filename
                        )
                        cert_filename, cert_ext = os.path.splitext(upd_file_name)
                        cert_filetype, _ = mimetypes.guess_type(upd_file_name)
                        certificate_file = DummyFile(
                            content=cert_data,
                            size=len(cert_data),
                            name=cert_filename,
                            ext=cert_ext,
                            content_type=cert_filetype                           
                        )
                        cert_url = docs.upload_file(certificate_file, s3_key)
                        _ = self.store_file(
                            file=certificate,
                            file_url=cert_url,
                            email_id=data_dict["email"],
                            filename=upd_file_name,
                        )
                    certificate.update({"certificate_url": cert_url})
                    all_certificates.append(certificate)

        # Add profile pictures
        profilePicUrl = "https://doloreschatbucket.s3.us-east-2.amazonaws.com/lawyer-connections/template-pp.png"

        if profile_picture.filename != "blob":
            profile_pic_data = await profile_picture.read()
            profile_pic_url = docs.upload_new_profile_picture(
                profile_pic_data, personnel_type
            )
            pic_id = Helpers.store_file(
                file=profile_picture,
                file_url=profile_pic_url,
                email_id=data_dict["email"],
                filename="user.png",
                readable=True,
            )
        else:
            pic_id = self.store_file(
                file=self.create_dummy_upload(profilePicUrl),
                file_url=profilePicUrl,
                email_id=data_dict["email"],
                filename="template-pp.png",
                readable=True,
            )
        sign_data = await lawpersonnel_sign.read()
        self.sign_saving(upload_info, sign_data, data_dict["email"])
        government_id_data = await government_id.read()
        governmentID = await docs.add_government_id(
            username, personnel_type, government_id_data, government_id.filename
        )
        lawpersonnel_data = {
            "email": data_dict["email"],
            "firstName": data_dict["firstName"],
            "lastName": data_dict["lastName"],
            "username": username,
            "profile_picture": f"{os.getenv('BACKEND')}image/{pic_id}/user.png",
            "professional_address": data_dict["professional_address"],
            "date_of_birth": data_dict["date_of_birth"],
            "contact_number": data_dict["contact_number"],
            "password": data_dict["password"],
            "authorize_verification": Helpers.get_boolean(
                data_dict["authorize_verification"]
            ),
            "consent_data_collection": Helpers.get_boolean(
                data_dict["consent_data_collection"]
            ),
            "receive_emails": Helpers.get_boolean(data_dict["receive_emails"]),
            "personnel_type": personnel_type[:-1],
            "law_firm_name": data_dict["law_firm_name"],
            "specialty": data_dict.get("specialty", None),
            "experience": data_dict.get("experience", None),
            "details": {
                "degree": data_dict["degree"],
                "institution_name": data_dict["institution_name"],
                "field_of_study": data_dict["field_of_study"],
                "graduation_year": data_dict["graduation_year"],
                "involved_in_legal_disputes": Helpers.get_boolean(
                    data_dict["involved_in_legal_disputes"]
                ),
                "legal_disputes_details": data_dict["legal_disputes_details"],
                "ongoing_investigations": (
                    Helpers.get_boolean(data_dict["ongoing_investigations"])
                    if "ongoing_investigations" in data_dict
                    else None
                ),
                "investigations_details": data_dict.get("investigations_details", None),
                "position_description": data_dict.get("position_description", None),
                "no_legal_education": (
                    Helpers.get_boolean(data_dict["no_legal_education"])
                    if "no_legal_education" in data_dict
                    else None
                ),
                "dismissed_or_resigned": (
                    Helpers.get_boolean(data_dict["dismissed_or_resigned"])
                    if "dismissed_or_resigned" in data_dict
                    else None
                ),
                "dismissal_details": data_dict.get("dismissal_details", None),
                "disqualified_or_revoked": (
                    Helpers.get_boolean(data_dict["disqualified_or_revoked"])
                    if "disqualified_or_revoked" in data_dict
                    else None
                ),
                "revocation_details": data_dict.get("revocation_details", None),
                "position": data_dict.get("position", None),
                "institution_address": data_dict.get("institution_address", None),
                "institution_contact": data_dict.get("institution_contact", None),
                "attending_another_institution": (
                    Helpers.get_boolean(data_dict["attending_another_institution"])
                    if "attending_another_institution" in data_dict
                    else None
                ),
                "other_institution_name": data_dict.get("other_institution_name", None),
                "other_degree": data_dict.get("other_degree", None),
                "start_year": data_dict.get("start_year", None),
                "end_year": data_dict.get("end_year", None),
                "has_professional_indemnity_insurance": (
                    Helpers.get_boolean(
                        data_dict["has_professional_indemnity_insurance"]
                    )
                    if "has_professional_indemnity_insurance" in data_dict
                    else None
                ),
                "insurance_coverage_details": data_dict.get(
                    "insurance_coverage_details", None
                ),
                "bar_association": data_dict.get("bar_association", None),
                "sanctioned_or_disciplined": (
                    Helpers.get_boolean(data_dict["sanctioned_or_disciplined"])
                    if "sanctioned_or_disciplined" in data_dict
                    else None
                ),
                "sanction_details": data_dict.get("sanction_details", None),
                "position": data_dict.get("position", None),
                "nature_of_practice": data_dict.get("nature_of_practice", None),
                "most_successful_case": data_dict.get("most_successful_case", None),
                "immigration_volume_per_year": data_dict.get(
                    "immigration_volume_per_year", None
                ),
                "source_of_funds": data_dict.get("source_of_funds", None),
                "politically_exposed_person": (
                    Helpers.get_boolean(data_dict["politically_exposed_person"])
                    if "politically_exposed_person" in data_dict
                    else None
                ),
            },
        }
        db_func.add_new_lawpersonnel(lawpersonnel_data)
        verification_items = {
            "professional_licenses": None,
            "government_ids": governmentID,
            "government_id_types": data_dict["government_id_type"],
            "address_documents": None,
            "bank_accounts": data_dict.get("bank_accounts", None),
        }
        db_func.add_lawpersonnel_info(
            data_dict["email"], personnel_type[:-1], all_experiences, all_certificates
        )
        if personnel_type == "lawyer":
            professional_license_data = await professional_licenses.read()
            address_proof_date = await address_proofs.read()
            license_urls, proof_urls = await docs.add_lawyer_verification_items(
                username,
                professional_licenses.filename,
                professional_license_data,
                address_proofs.filename,
                address_proof_date,
            )
            verification_items["professional_licenses"] = license_urls
            verification_items["address_documents"] = proof_urls

        db_func.add_lawpersonnel_verification_items(
            data_dict["email"], personnel_type[:-1], verification_items
        )
        user = db_func.get_lawpersonnel(data_dict["email"])
        self.update_lawyer_to_team(user)

        schedule_date = datetime.now(timezone.utc) + timedelta(days=1)
        scheduler.schedule_task(
            self.background_lawpersonnel_verification, schedule_date, user=user
        )

    def _is_image(self, filename: str) -> bool:
        return any(filename.lower().endswith(ext) for ext in self.image_extensions)

    def background_lawpersonnel_verification(self, user: LawPersonnel) -> None:
        verification_items = db_func.get_lawpersonnel_verification_items(
            lawpersonnel_email=user.email, lawpersonnel_type=user.personnel_type
        )
        govt_id_url = verification_items[0].get("government_id", None)
        govt_id_type = verification_items[0].get("government_id_type", None)
        file_data = docs.download_file(govt_id_url) if govt_id_url else None
        if file_data and self._is_image(file_data["filename"]):
            govt_id_bytes = file_data["image_data"]
        else:
            govt_id_bytes = file_data["content"]
        file_bytes = {
            "government_id": govt_id_bytes,
        }
        provided_data = {
            "full_legal_name": user.full_legal_name,
            "date_of_birth": user.date_of_birth,
            "id_type": govt_id_type,
        }
        if user.personnel_type == "lawyer":
            provided_data["bar_id"] = user.details["bar_association"]
        is_verified, verification_error = Helpers.verify_lawpersonnel(user.username)
        if is_verified:
            db_func.verify_lawpersonnel(user.email)
            Email.send_verification_success(
                user.email, user.full_legal_name, user.personnel_type
            )

        else:
            user_dir = f"{user.personnel_type}/{user.username}/"
            Email.send_verification_failure(
                user.email, user.full_legal_name, verification_error
            )
            db_func.delete_lawpersonnel_verification_items(
                lawpersonnel_email=user.email, lawpersonnel_type=user.personnel_type
            )
            db_func.delete_lawpersonnel_info(
                lawpersonnel_email=user.email, lawpersonnel_type=user.personnel_type
            )
            db_func.delete_lawpersonnel(user.email)
            docs.delete_user_directory(user_dir)
            # create an endpoint to reapply for verification
