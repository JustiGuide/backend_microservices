import asyncio
from datetime import datetime, timedelta, timezone
import io
import mimetypes
import os
import random
import string
import re
from typing import Any, Literal, Union
from fastapi import UploadFile, HTTPException
from pydantic import BaseModel, EmailStr
import requests
from documents_gateway import DocumentsGateway


class UploadFile_Dummy(BaseModel):
    size: int
    content_type: str

class Helpers:

    @staticmethod
    def format_date(date: datetime) -> str:
        today = datetime.now(timezone.utc).date()
        if date == today:
            return "Today"
        elif date == today - timedelta(days=1):
            return "Yesterday"
        else:
            return date.strftime("%m/%d/%y")

    @staticmethod
    def get_file_size(file_size: int) -> str:
        if file_size < 1024:
            return f"{file_size} B"
        elif file_size < 1024**2:
            return f"{file_size / 1024:.2f} KB"
        elif file_size < 1024**3:
            return f"{file_size / 1024**2:.2f} MB"
        else:
            return f"{file_size / 1024**3:.2f} GB"

    @staticmethod
    def get_url_file_size(file_url: str) -> str:
        response = requests.head(file_url, timeout=10)
        response.raise_for_status()
        return Helpers.get_file_size(int(response.headers.get('Content-Length')))

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
    def store_file(file: Union[UploadFile, UploadFile_Dummy], file_url: str, email_id: EmailStr, filename: str, readable: bool = False) -> str:
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

    @staticmethod
    def get_form_context(form_name: str) -> dict:
        # TODO: Call Documents Service to read form context
        pass

    @staticmethod
    def get_site_context(site: str = Literal["immigrant", "lawpersonnel"]) -> dict:
        # TODO: Call Documents Service to read site context
        pass

    @staticmethod
    def get_form_fieldmap(form_name: str) -> dict:
        # TODO: Call Documents Service to read form fieldmap
        pass

    @staticmethod
    def get_form_analysis(form_name: str) -> dict:
        # TODO: Call Documents Service to read form analysis
        pass

    @staticmethod
    def get_supported_forms() -> list[str]:
        # documents_service_url = os.getenv("DOCUMENTS_SERVICE_URL")
        # if not documents_service_url:
        #     raise HTTPException(
        #         status_code=500,
        #         detail="Documents service URL is not configured.",
        #     )

        # endpoint = f"{documents_service_url.rstrip('/')}/forms"
        # try:
        #     response = requests.get(endpoint, timeout=10)
        #     response.raise_for_status()
        # except requests.RequestException as exc:
        #     raise HTTPException(
        #         status_code=503,
        #         detail=f"Unable to reach Documents Service: {exc}",
        #     ) from exc

        # try:
        #     payload = response.json()
        # except ValueError as exc:
        #     raise HTTPException(
        #         status_code=502,
        #         detail="Documents Service returned invalid JSON.",
        #     ) from exc

        # forms: list[str] = []
        # if isinstance(payload, list):
        #     forms = [str(item) for item in payload]
        # elif isinstance(payload, dict):
        #     for key in ("forms", "supported_forms", "data"):
        #         value = payload.get(key)
        #         if isinstance(value, list):
        #             forms = [str(item) for item in value]
        #             break
        # if not forms:
        #     raise HTTPException(
        #         status_code=502,
        #         detail="Documents Service response did not include a forms list.",
        #     )
        # return forms
        # TODO: Connect with documents service
        pass

    @staticmethod
    def get_message_time(message_time: str) -> tuple[str, datetime]:
        if not isinstance(message_time, str):
            timestamp = message_time
        else:
            try:
                timestamp = datetime.strptime(message_time, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                timestamp = datetime.strptime(message_time, "%Y-%m-%d %H:%M:%S")

        date = Helpers.format_date(timestamp.date())
        return date, timestamp

    @staticmethod
    def date_sort_key(date_str: str) -> datetime:
        if date_str == "Today":
            return datetime.now().date()
        elif date_str == "Yesterday":
            return datetime.now().date() - timedelta(days=1)
        else:
            return datetime.strptime(date_str, "%m/%d/%y").date()

    @staticmethod
    def sort_ai_messages(
        ai_message_history: dict[
            str, dict[str, dict[str, Union[str, list[str], bool, list[str]]]]
        ],
    ):
        grouped_msgHist: dict[
            str, list[dict[str, Union[str, dict[str, list[str]], datetime]]]
        ] = {}
        for sender, messages in ai_message_history.items():
            if sender != "form":
                for msg_id, msg_data in messages.items():
                    date, timestamp = Helpers.get_message_time(msg_data["timestamp"])
                    documentNames = [
                        {
                            "url": url,
                            "name": url.split("/")[-1],
                            "size": msg_data["document_sizes"][i],
                        }
                        for i in range(len(msg_data["documents"]))
                        if (url := msg_data["documents"][i]) is not None
                    ]
                    message_info = {
                        "message_id": msg_id,
                        "sender": sender,
                        "message": msg_data["message"],
                        "vote": msg_data["vote"],
                        "references": msg_data["references"],
                        "timestamp": timestamp,
                        "documents": documentNames,
                    }
                    if date not in grouped_msgHist:
                        grouped_msgHist[date] = []
                    grouped_msgHist[date].append(message_info)

        for date in grouped_msgHist:
            grouped_msgHist[date].sort(key=lambda x: x["timestamp"])
            for msg in grouped_msgHist[date]:
                timeVal = msg["timestamp"]
                msg["timestamp"] = timeVal.strftime("%I:%M %p").lstrip("0")

        sorted_msgHist = dict(
            sorted(grouped_msgHist.items(), key=lambda x: Helpers.date_sort_key(x[0]))
        )
        return sorted_msgHist

    @staticmethod
    def retreive_ai_messages_for_autofill(
        ai_message_history: dict[
            str, dict[str, dict[str, Union[str, list[str], bool, list[str]]]]
        ],
        limit: int = 50
    ):
        grouped_msgHist: list[dict[str, Union[str, dict[str, list[str]], datetime]]] = []
        for sender, messages in ai_message_history.items():
            for msg_id, msg_data in messages.items():
                date, timestamp = Helpers.get_message_time(msg_data["timestamp"])
                documentNames = [
                    {
                        "url": url,
                        "name": url.split("/")[-1],
                        "size": msg_data["document_sizes"][i],
                    }
                    for i in range(len(msg_data["documents"]))
                    if (url := msg_data["documents"][i]) is not None
                ]
                message_info = {
                    "message_id": msg_id,
                    "sender": sender,
                    "message": msg_data["message"],
                    "vote": msg_data["vote"],
                    "references": msg_data["references"],
                    "timestamp": timestamp,
                    "documents": documentNames,
                }
                if len(grouped_msgHist) < limit*2:
                    grouped_msgHist.append(message_info)

        sorted_messages = sorted(grouped_msgHist, key=lambda x:x["timestamp"])
        return sorted_messages

    @staticmethod
    async def get_wave_buffer(audio_content: bytes):
        try:
            command = ["ffmpeg", "-i", "-", "-f", "wav", "-"]
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            wav_output, stderr = await process.communicate(input=audio_content)
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {stderr.decode()}")
            wav_buffer = io.BytesIO(wav_output)
            # wav_buffer.seek(0)
            return wav_buffer
        except Exception as e:
            print(f"Error processing audio file: {e}")
            return None

    @staticmethod
    def get_casetype(form_name: str = Literal["i129", "i130", "i589", "i765", "n400"]) -> str:
        all_case_types = Helpers.get_all_casetypes()
        for case_type, case_info in all_case_types.items():
            if case_info["form"] == form_name:
                return case_type
        # TODO: Connect with case management service to get case type based on form_name (case_type.json)
        pass

    @staticmethod
    def get_all_casetypes() -> dict[str, dict[str, Union[str, list[dict[str, Union[str, int]]]]]]:
        # TODO: Connect with case management service to get case type based on form_name (case_type.json)
        pass

    @staticmethod
    def get_formname_from_case(case_type: str) -> str:
        all_case_types = Helpers.get_all_casetypes()
        return all_case_types[case_type]["form"]
        # TODO: Connect with case management service to get forma name based on the case_type (case_type.json)

    @staticmethod
    def retrieve_connected_lawyers(
        immigrant_email: EmailStr, case_id: str = None, only_emails: bool = False
    ) -> list[dict[str, Union[str, bool, list[str]]]]:
        # TODO: Connect with relationship microservice
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

        pass

    @staticmethod
    def create_dummy_upload(local_file_path: str) -> UploadFile_Dummy:
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
    def add_notification(receiver: EmailStr, sender: EmailStr, type: Literal["cases", "tasks", "connection", "kyc", "forms", "teams", "lawyer_chat", "intake", "case_payment"], content: str, target_id: dict[str, Any], one_time:bool=False, created_at:datetime=None):
        # TODO: connect with user management service
        # db = db_func.Session()
        # if created_at is None:
        #     notification_alert = NotificationAlerts(
        #         receiver = receiver.lower(),
        #         sender = sender.lower(),
        #         type = type,
        #         content = content,
        #         target_id = target_id,
        #         one_time = one_time
        #     )
        #     db.add(notification_alert)

        # if type == "kyc":
        #     notification_alert = db.query(NotificationAlerts).filter(NotificationAlerts.receiver == receiver.lower(), NotificationAlerts.type == type, NotificationAlerts.target_id == target_id).first()
        #     if notification_alert:
        #         notification_alert.update_created_at()
        #         db.commit()
        # else:
        #     notification_alert = NotificationAlerts(
        #         receiver = receiver.lower(),
        #         sender = sender.lower(),
        #         type = type,
        #         content = content,
        #         target_id = target_id,
        #         one_time = one_time,
        #         created_at = created_at
        #     )
        #     db.add(notification_alert)

        # db.commit()
        pass

    @staticmethod
    def is_image_file(filename: str) -> bool:
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
        return any(filename.lower().endswith(ext) for ext in image_extensions)

    @staticmethod
    def calculate_experience_level(years: int) -> str:
        if not isinstance(years, (int, float)):
            return "mid"

        if years <= 3:
            return "entry"
        elif years <= 10:
            return "mid"
        else:
            return "senior"

    @staticmethod
    def kyc_map(kyc_data: dict[str, str], kyc_map: dict) -> dict[str, list[str]]:
        values: dict[str, list[str]] = {}
        if not isinstance(kyc_data, dict):
            return {}

        for key, value in kyc_data.items():
            if key in kyc_map:
                kyc_mp: dict = kyc_map[key]
                question = kyc_mp.get("value")
                if not question:
                    continue

                if question not in values:
                    values[question] = []

                answers_to_add = []
                raw_answers = value if isinstance(value, list) else [value]

                for val in raw_answers:
                    answer = kyc_mp.get(str(val))
                    if "textboxes" in kyc_mp and isinstance(kyc_mp["textboxes"], dict):
                        if kyc_mp["textboxes"].get("assoc") == answer:
                            answer_key = next(
                                (k for k in kyc_mp["textboxes"] if k != "assoc"), None
                            )
                            if answer_key and answer_key in kyc_data:
                                answer = kyc_data[answer_key]

                    if answer is not None:
                        answers_to_add.append(str(answer))

                if answers_to_add:
                    current_answers = set(values[question])
                    for ans in answers_to_add:
                        if ans not in current_answers:
                            values[question].append(ans)
                            current_answers.add(ans)

        for q in values:
            values[q] = [
                str(item).strip()
                for item in values[q]
                if item is not None and str(item).strip()
            ]
            if not values[q]:
                del values[q]

        return values

    @staticmethod
    def get_random_n400_question(previous_n400_quiz: list[dict[str, str]]):
        asked_questions = [question[f"question_{i+1}"] for i, question in enumerate(previous_n400_quiz)
        ]
        n400_questions = DocumentsGateway.get_n400_quiz()

        valid_n400_questions = [
            i
            for i, question in enumerate(n400_questions)
            if question["question"] not in asked_questions
        ]
        random_question = (
            random.choice(valid_n400_questions)
            if len(valid_n400_questions) > 0
            else None
        )
        if random_question:
            question = n400_questions[random_question]["question"]
            correct_option = n400_questions[random_question]["correct_options"]
            incorrect_options = n400_questions[random_question]["incorrect_options"]
            if len(incorrect_options) > 3:
                incorrect_options = random.sample(incorrect_options, 3)
            if len(correct_option) > 1:
                correct_option = random.sample(correct_option, 1)
            option_selection = random.choice(["A", "B", "C", "D"])
            return {
                "question": question,
                "options": {
                    "A": (
                        correct_option[0]
                        if option_selection == "A"
                        else incorrect_options.pop(0)
                    ),
                    "B": (
                        correct_option[0]
                        if option_selection == "B"
                        else incorrect_options.pop(0)
                    ),
                    "C": (
                        correct_option[0]
                        if option_selection == "C"
                        else incorrect_options.pop(0)
                    ),
                    "D": (
                        correct_option[0]
                        if option_selection == "D"
                        else incorrect_options.pop(0)
                    ),
                },
                "answer": option_selection,
            }
        else:
            return None
