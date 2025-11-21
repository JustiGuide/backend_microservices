from fastapi import HTTPException, Request
from pydantic import BaseModel
from typing import Any, Literal, Optional, Dict
from sqlalchemy.orm import Session
import os, hmac, hashlib
from lob_python import ApiClient, Configuration
from lob_python.api.addresses_api import AddressesApi
from lob_python.model.ltr_use_type import LtrUseType
from lob_python.model.address_editable import AddressEditable
from lob_python.model.letter_editable import LetterEditable
from lob_python.model.country_extended import CountryExtended
from lob_python.api.addresses_api import AddressesApi
from lob_python.api.letters_api import LettersApi
from lob_python.model.metadata_model import MetadataModel
from lob_python.exceptions import ApiException
from email_gateway import Email
from database import Functions
from documents_gateway import DocumentsGateway

db_func = Functions()
docs = DocumentsGateway()


class CreateAddressInput(BaseModel):
    type: str = Literal["user_form_address", "uscis_mailing_address"]
    name: str
    email: str
    address_line1: str
    address_city: str
    address_state: str
    address_zip: str
    address_country: str = "US"
    company: str = None
    phone: str = None
    description: str = None
    metadata: dict[str, Any] = None


class UsernameFormInput(BaseModel):
    username: str
    form_name: str = "N400"
    file_url: str = None


class AddressIdInput(BaseModel):
    address_id: str


class CreateLetterInput(BaseModel):
    to_address_id: str
    from_address_id: str
    file_url: str
    use_type: str = "operational"
    color: bool = True


class LobMailing:
    def __init__(self):
        self.lob_environment = os.getenv("LOB_ENVIRONMENT", "staging")
        self.lob_secret_key = (
            os.getenv("LOB_TEST_SECRET_KEY")
            if self.lob_environment == "staging"
            else os.getenv("LOB_LIVE_SECRET_KEY")
        )
        self.configuration = Configuration(
            host="https://api.lob.com/v1", username=self.lob_secret_key
        )
        self.address_key_map = {
            "i129": {
                "physical_address": None,
                "is_mailing_different": None,
                "mailing_address": {
                    "in_care_of": "mailingCareOf",
                    "street_address": "mailingStreet",
                    "unit_type": {
                        "key": "mailingUnitType",
                        "options": {
                            "mailingApt": "Apt.",
                            "mailingSte": "Ste.",
                            "mailingFlr": "Flr.",
                        },
                    },
                    "unit_number": "mailingUnitNumber",
                    "city": "mailingCity",
                    "state": "mailingState",
                    "zip": "mailingZip",
                    "province": "mailingProvince",
                    "postal_code": "mailingPostalCode",
                    "country": "mailingCountry",
                },
            },
            "i765": {
                "physical_address": None,
                "is_mailing_different": None,
                "mailing_address": {
                    "in_care_of": "mailingCareOf",
                    "street_address": "mailingStreet",
                    "unit_type": {
                        "key": "mailingUnitType",
                        "options": {
                            "mailingApt": "Apt.",
                            "mailingSte": "Ste.",
                            "mailingFlr": "Flr.",
                        },
                    },
                    "unit_number": "mailingUnitNumber",
                    "city": "mailingCity",
                    "state": "mailingState",
                    "zip": "mailingZip",
                    "province": None,
                    "postal_code": None,
                    "country": "United States",
                },
            },
            "i130": {
                "physical_address": None,
                "is_mailing_different": None,
                "mailing_address": {
                    "in_care_of": "mailingCareOf",
                    "street_address": "mailingStreet",
                    "unit_type": {
                        "key": "mailingUnitType",
                        "options": {
                            "mailingApt": "Apt.",
                            "mailingSte": "Ste.",
                            "mailingFlr": "Flr.",
                        },
                    },
                    "unit_number": "mailingUnitNumber",
                    "city": "mailingCity",
                    "state": "mailingState",
                    "zip": "mailingZip",
                    "province": "mailingProvince",
                    "postal_code": "mailingPostalCode",
                    "country": "United States",
                },
            },
            "i589": {
                "physical_address": {
                    "in_care_of": None,
                    "street_address": "part-a-i-a-i-street",
                    "unit_number": "part-a-i-a-i-apt",
                    "unit_type": None,
                    "city": "part-a-i-a-i-city",
                    "state": "part-a-i-a-i-state",
                    "zip": "part-a-i-a-i-zipCode",
                    "province": None,
                    "postal_code": None,
                    "country": "United States",
                },
                "is_mailing_different": None,
                "mailing_address": {
                    "in_care_of": "part-a-i-a-i-mailCO",
                    "street_address": "part-a-i-a-i-mailStreet",
                    "unit_type": None,
                    "unit_number": "part-a-i-a-i-mailApt",
                    "city": "part-a-i-a-i-mailCity",
                    "state": "part-a-i-a-i-mailState",
                    "zip": "part-a-i-a-i-mailZipCode",
                    "province": None,
                    "postal_code": None,
                    "country": "United States",
                },
            },
            "n400": {
                "physical_address": {
                    "in_care_of": "phys_add_care_of",
                    "street_address": "phys_add_street",
                    "unit_type": {
                        "key": "phys_add_unit",
                        "options": {"apt": "Apt.", "ste": "Ste.", "flr": "Flr."},
                    },
                    "unit_number": "phys_add_unit_num",
                    "city": "phys_add_city",
                    "state": "phys_add_state",
                    "zip": "phys_add_zip",
                    "province": "phys_add_province",
                    "postal_code": "phys_add_postal",
                    "country": "phys_add_country",
                },
                "is_mailing_different": "is_mailing",
                "mailing_address": {
                    "in_care_of": "mail_add_care_of",
                    "street_address": "mail_add_street",
                    "unit_type": {
                        "key": "mail_add_unit",
                        "options": {"apt": "Apt.", "ste": "Ste.", "flr": "Flr."},
                    },
                    "unit_number": "mail_add_unit_num",
                    "city": "mail_add_city",
                    "state": "mail_add_state",
                    "zip": "mail_add_zip",
                    "province": "mail_add_province",
                    "postal_code": "mail_add_postal",
                    "country": "mail_add_country",
                },
            },
        }

    def generate_uscis_unique_key(self, center_name: str):
        return f"uscis_{center_name.lower().replace(' ', '_')}"

    def generate_user_unique_key(self, payload: CreateAddressInput):
        return f"user_{payload.name.lower().replace(' ', '_')}_{payload.address_zip}"

    def create_address(self, payload: CreateAddressInput, form_name: str = "N400"):
        address_type = payload.type
        metadata = payload.metadata or {}
        if address_type == "uscis_form_address":
            center_name = metadata.get("center_name") or payload.name
            unique_key = self.generate_uscis_unique_key(center_name)
            metadata.update(
                {
                    "unique_key": unique_key,
                    "type": "uscis_form_address",
                    "notes": f"Official USCIS address for {center_name}",
                }
            )
        elif address_type == "user_mailing_address":
            unique_key = self.generate_user_unique_key(payload)
            metadata.update(
                {
                    "unique_key": unique_key,
                    "type": "user_mailing_address",
                }
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid address type. Must be 'uscis_form_address' or 'user_mailing_address'.",
            )
        try:
            with ApiClient(self.configuration) as api_client:
                api_instance = AddressesApi(api_client)

                metadata = payload.metadata or {}
                flat_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, list):
                        flat_metadata[key] = ",".join(value)
                    else:
                        flat_metadata[key] = str(value)

                metadata_model = (
                    MetadataModel(**flat_metadata) if flat_metadata else None
                )

                address_editable = AddressEditable(
                    name=payload.name,
                    address_line1=payload.address_line1,
                    address_city=payload.address_city,
                    address_state=payload.address_state,
                    address_zip=payload.address_zip,
                    address_country=CountryExtended(payload.address_country),
                    company=payload.company,
                    phone=payload.phone,
                    email=payload.email,
                    description=payload.description,
                    metadata=metadata_model,
                )

                api_response = api_instance.create(address_editable)

                address_creation_response = api_response.to_dict()

                # Save New Lob Record
                db_func.save_lob_record(
                    username=payload.metadata.get("jg_username", "justiguide_user"),
                    lob_id=address_creation_response.get("id"),
                    lob_type="address",
                    form_name=form_name,
                    metadata={"type": "user_mailing_address"},
                )

                print(
                    f"-	Address Created Successfully: {address_creation_response.get('id')}"
                )

                return address_creation_response
        except ApiException as e:
            raise HTTPException(status_code=400, detail=f"Lob APIException: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected Error: {str(e)}")

    def generate_address(self, payload: UsernameFormInput):
        user_data = db_func.get_immigrant(payload.username)

        if not user_data:
            raise HTTPException(status_code=404, detail="User not found.")

        address_data = {
            "type": "user_mailing_address",
            "name": user_data.full_legal_name,
            "address_line1": "1159 Guerrero Street",
            "address_line2": None,
            "address_city": "San Francisco",
            "address_state": "CA",
            "address_zip": "94110",
            "address_country": "US",
            "company": "JustiGuide",
            "phone": None,
            "email": user_data.email if user_data.email else "info@justiguide.com",
            "description": "JustiGuide Mailing Address in San Francisco",
            "metadata": {
                "jg_username": user_data.username,
                "notes": f"{(user_data.first_name).capitalize()}'s USCIS Mailing Address.",
            },
        }
        user_address_dict = {}
        try:
            user_form_data = db_func.retrieve_form_details(payload.form_name, user_data.email)
            important_keys = self.address_key_map[payload.form_name.lower()]
            if (
                user_form_data.get(important_keys["is_mailing_different"], None)
                or not important_keys["physical_address"]
            ):
                address_keys = important_keys["mailing_address"]
            else:
                address_keys = important_keys["physical_address"]

            first_line = []
            if user_form_data.get(address_keys["in_care_of"]):
                first_line.append(user_form_data.get(address_keys["in_care_of"]))
            if user_form_data.get(address_keys["street_address"]):
                first_line.append(user_form_data.get(address_keys["street_address"]))
            user_address_dict["address_line1"] = (
                " ".join(first_line) if first_line else None
            )
            second_line = []
            if address_keys.get("unit_type") and user_form_data.get(
                address_keys["unit_type"]["key"]
            ):
                second_line.append(
                    address_keys["unit_type"]["options"][
                        user_form_data.get(address_keys["unit_type"]["key"])
                    ]
                )
            if user_form_data.get(address_keys["unit_number"]):
                second_line.append(user_form_data.get(address_keys["unit_number"]))

            user_address_dict["address_line2"] = (
                " ".join(second_line) if second_line else None
            )
            user_address_dict["address_city"] = user_form_data.get(
                address_keys["city"], None
            )
            user_address_dict["address_state"] = user_form_data.get(
                address_keys.get("state", "province"), None
            )
            user_address_dict["address_zip"] = user_form_data.get(
                address_keys.get("zip", "postal_code"), None
            )
            user_address_dict["address_country"] = user_form_data.get(
                address_keys["country"], None
            )
        except Exception as exp:
            print(f"Error/Exception Occurred: {exp}")

        for key, value in user_address_dict.items():
            if value is not None:
                address_data[key] = value
        return address_data

    def create_user_address(self, payload: UsernameFormInput):
        user_address = self.check_user_address(payload)
        if user_address:
            return user_address

        address_data = self.generate_address(payload)
        try:
            address_payload = CreateAddressInput(**address_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")

        return self.create_address(address_payload, payload.form_name)

    def list_addresses(self):
        try:
            with ApiClient(self.configuration) as api_client:
                api_instance = AddressesApi(api_client)
                addresses = api_instance.list(limit=10)
                return addresses.to_dict()
        except ApiException as e:
            raise HTTPException(status_code=400, detail=f"Lob APIException: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected Error: {str(e)}")

    def check_address(self, payload: AddressIdInput):
        try:
            with ApiClient(self.configuration) as api_client:
                api = AddressesApi(api_client)
                address = api.get(payload.address_id)
                return address.to_dict()
        except ApiException as e:
            print(e)

    def check_user_address(self, payload: UsernameFormInput):
        try:
            with ApiClient(self.configuration) as api_client:
                api = AddressesApi(api_client)
                addresses = api.list()
                username_address = [
                    address
                    for address in addresses.data
                    if "metadata" in address
                    and address["metadata"].get("jg_username") == payload.username
                ]

                if username_address:
                    return username_address[0]
                return None
        except ApiException as e:
            print(f"Lob API Error: {e}")
        except Exception as e:
            print(f"Unexpected Error: {e}")

    def delete_address(self, payload: AddressIdInput):
        try:
            with ApiClient(self.configuration) as api_client:
                api = AddressesApi(api_client)
                print(f"-	Deleting Address: {payload.address_id}")
                deleted_resource = api.delete(payload.address_id)
                deleted = db_func.delete_lob_record_by_id(lob_id=payload.address_id, lob_type="address")
                if deleted:
                    print("-	Address record also removed from local DB.")
        except ApiException as e:
            print(e)

    def compare_addresses(self, user_address: dict, form_address: dict) -> bool:
        user_address_cleaned = {
            k: v
            for k, v in user_address.items()
            if k not in ["id", "date_created", "date_modified", "object"]
        }

        if "metadata" in user_address_cleaned:
            user_address_cleaned["metadata"] = {
                k: v
                for k, v in user_address_cleaned["metadata"].items()
                if k not in ["type", "unique_key"]
            }

        return sorted(user_address_cleaned.items()) == sorted(form_address.items())

    def send_letter_prep(self, payload: UsernameFormInput):
        try:
            user_address = self.check_user_address(payload)
            user_address_id = None
            form_address = self.generate_address(payload)
            if not user_address:
                print("-	User Doesn't Have An Address Saved.")
                new_address = self.create_user_address(payload)
                if new_address:
                    print("-	New Lob Address Has Been Created For User.")
                    user_address_id = new_address.get("id")

            elif not self.compare_addresses(user_address, form_address):
                print(user_address)
                self.delete_address(AddressIdInput(address_id=user_address.get("id")))
                print("-	User Address Has Changed, Updating Address.")
                updated_address = self.create_address(
                    CreateAddressInput(**form_address), payload.form_name
                )
                if updated_address:
                    print("-	User Address Has Been Updated Successfully.")
                    user_address_id = updated_address.get("id")
            else:
                print("-	User Already Has An Address Saved, This is Great!")
                user_address_id = user_address.get("id")

            if user_address_id:
                form_link = (
                    payload.file_url
                    if payload.file_url
                    else f"https://doloreschatbucket.s3.us-east-2.amazonaws.com/users/{payload.username}/forms/{(payload.form_name).lower()}_compiled_application.pdf"
                )

                docs.add_empty_first_page(form_link)
                phoenix_lockbox_id = "adr_247d48241717f66c"
                send_letter_data = {
                    "to_address_id": phoenix_lockbox_id,
                    "from_address_id": user_address_id,
                    "file_url": form_link,
                }
                print("-	Letter Prepped To Be Sent.")
                new_letter = CreateLetterInput(**send_letter_data)
                return self.send_letter(new_letter, payload.username, payload.form_name)

        except Exception as exp:
            print("-	Letter Was Not Sent.")
            raise exp

    def send_letter(
        self, payload: CreateLetterInput, username: str, form_name: str = "N400"
    ):
        try:
            with ApiClient(self.configuration) as api_client:
                letter_api = LettersApi(api_client)

                letter_editable = LetterEditable(
                    to=payload.to_address_id,
                    _from=payload.from_address_id,
                    file=payload.file_url,
                    use_type=LtrUseType("operational"),  # fixed type
                    color=payload.color,
                )

                api_response = letter_api.create(letter_editable)

                lob_letter_response = api_response.to_dict()

                db_func.save_lob_record(
                    username=username,
                    lob_id=lob_letter_response.get("id"),
                    lob_type="letter",
                    form_name=form_name,
                    metadata={"destination": "phoenix_lockbox"},
                )

                print("-	Congratulations, The Letter Has Been Sent.")
                sent_file_url = lob_letter_response["url"]
                docs.upload_web_file(
                    sent_file_url,
                    payload.file_url.removeprefix(docs.base_url)
                )
                return lob_letter_response

        except ApiException as e:
            raise HTTPException(status_code=400, detail=f"Lob APIException: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected Error: {str(e)}")

    def verify_signature(self, body: bytes, signature: str, timestamp: str) -> bool:
        secret = os.getenv("LOB_TEST_WEBHOOK_SECRET")
        if not secret:
            print("LOB_TEST_WEBHOOK_SECRET not set.")
            return False

        signed_payload = timestamp.encode("utf-8") + b"." + body
        expected_sig = hmac.new(
            secret.encode("utf-8"), signed_payload, hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(expected_sig, signature):
            return True

        print(f"Signature mismatch: expected={expected_sig} received={signature}")
        return False

    async def handle_webhook(self, request: Request, signature: str, timestamp: str):
        body = await request.body()
        if not self.verify_signature(body, signature, timestamp):
            raise HTTPException(status_code=401, detail="Invalid Lob Signature")

        data: dict = await request.json()
        event_type = data.get("event_type")
        resource: dict = data.get("data", {})

        print(
            f"[Webhook] Event Received: {event_type} for resource ID: {resource.get('id')}"
        )

        jg_username = resource.get("metadata", {}).get("jg_username", "justiguide_user")
        jg_user_email = resource.get("from_address", {}).get(
            "email", "info@justiguide.com"
        )

        # Store event in DB
        db_func.save_lob_record(
            username=jg_username,
            lob_id=resource.get("id"),
            lob_type="letter_event",
            form_name="N/A",
            metadata={"event": "lob_webhook", "event_type": event_type},
        )
        sender = db_func.get_immigrant(jg_user_email) or db_func.get_lawpersonnel(jg_user_email)
        try:
            if event_type == "letter.created":
                print(f"[Webhook] Letter Created: {resource.get('id')}")
            elif event_type == "letter.delivered":
                print(f"[Webhook] Letter Delivered: {resource.get('id')}")
                Email.send_form_delivery_notification(
                    sender_email=jg_user_email,
                    sender_name=sender.full_legal_name,
                    letter_id=resource.get("id"),
                    form_name="N/A"
                )
            elif event_type == "letter.failed":
                print(f"[Webhook] Letter Failed: {resource.get('id')}")
            else:
                print(f"[Webhook] Unhandled event type: {event_type}")

            return {"status": "received"}
        except Exception as e:
            print(f"[Webhook] Error handling event {event_type}: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error handling event: {str(e)}"
            )
