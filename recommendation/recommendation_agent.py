import os
import json
import time
from typing import Literal, Union
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr
from rag_gateway import RAGGateway
from database import Functions, Immigrants
from helpers import Helpers
from response_schemas import GeneratedLawyerRecommendations
from .recommendation_prompts import generate_recommendation_prompt

load_dotenv()

rag_app = RAGGateway()
db_func = Functions()

class Recommender:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    def _create_tool_from_pydantic(
        self, model: type[BaseModel], function_name: str
    ) -> dict:
        """Creates an OpenAI Tool definition from a Pydantic model."""
        schema = model.model_json_schema()
        model_description = schema.get("description", f"Schema for {model.__name__}")

        tool = {
            "type": "function",
            "function": {
                "name": function_name,
                "description": model_description,
                "parameters": schema,
            },
        }
        return tool

    def _get_non_file_data(
        self, immigrant_username: str
    ) -> dict[str, Union[dict[str, Union[str, list[str]]], list[str]]]:
        user_data = {}
        kyc_data = {}
        messages = []
        try:
            immigrant = db_func.get_immigrant(immigrant_username)
            if immigrant:
                user_data = {
                    key: value
                    for key, value in immigrant.extract_data().items()
                    if key in ["first_name", "last_name", "location", "email"]
                }
                kyc_map = rag_app.load_kyc_map()
                raw_kyc = db_func.get_immigrant_kyc(immigrant.email)
                kyc_data = Helpers.kyc_map(raw_kyc, kyc_map)

                message_history = db_func.process_immigrant_messages(
                    immigrant_email=immigrant.email
                )
                messages = [message_history["user"][uuid]["message"] for uuid in message_history["user"] if len(message_history.keys()) > 0 and "user" in message_history]
        except Exception as e:
            print(
                f"Error fetching non-file data for user '{immigrant_username}': {e}"
            )

        return {"user_info": user_data, "kyc": kyc_data, "messages": messages}

    def presort_lawyers(
        self,
        immigrant: Immigrants,
    ) -> tuple[
        list[dict[str, Union[str, EmailStr]]],
        list[dict[str, Union[str, EmailStr]]],
        dict[EmailStr, Union[str, bool]],
        dict[EmailStr, Union[str, bool]],
        dict[EmailStr, Union[str, bool]],
        dict[str, Union[str, EmailStr]],
    ]:
        dummy_lawyers = [
            "codyfisher@fisherlaw.com",
            "devon.lane@foxlegal.com",
            "drobertson@robertsonllc.com",
            "guy.hawkins@robertsonllc.com",
            "carter.elizabeth1965@gmail.com",
        ]
        connected_lawyers = db_func.retrieve_connected_lawyers(immigrant_email=immigrant.email, only_emails=True)
        pending_lawyers = {
            email: details
            for email, details in db_func.retrieve_invitation_data(
                invited_type="pending_client", invitee_email=immigrant.email
            ).items()
            if email not in connected_lawyers
        }
        invited_external_lawyers = {
            email: details
            for email, details in db_func.retrieve_invitation_data(
                invited_type="invited_external_lawyer", invitee_email=immigrant.email
            ).items()
            if email not in connected_lawyers
        }
        immigrant_data = {
            "username": immigrant.username,
            "location": immigrant.location,
            "email": immigrant.email,
        }
        preRec_regLawyers = []
        pending_regLawyers = {}
        preRec_unregLawyers = []
        invited_unregLawyers = {}
        preRec_dummyLawyers = {}
        registered_lawyers = db_func.retrieve_verified_lawyers()
        unregistered_lawyers = db_func.retrieve_external_lawyers()
        excluded_reglawyers = dummy_lawyers.copy()
        excluded_reglawyers.extend(connected_lawyers)
        excluded_reglawyers.extend(list(pending_lawyers.keys()))
        for lawyer in registered_lawyers:
            if lawyer.email not in excluded_reglawyers:
                preRec_regLawyers.append(
                    {
                        "username": lawyer.username,
                        "email": lawyer.email,
                        "full_name": f"{lawyer.full_legal_name}",
                        "law_firm": lawyer.law_firm_name,
                        "experience": lawyer.experience,
                        "expertise": lawyer.specialty,
                        "location": lawyer.professional_address,
                    }
                )
            elif lawyer.email in list(pending_lawyers.keys()):
                pending_regLawyers[lawyer.email] = {
                    "Point of Contact": f"{lawyer.full_legal_name}",
                    "Law Firm Name": lawyer.law_firm_name,
                    "Experience": lawyer.experience,
                    "Expertise": lawyer.specialty,
                    "Main Office": lawyer.professional_address,
                    "Phone Number": lawyer.contact_number,
                    "Image link": lawyer.profile_picture,
                    "Email Address": lawyer.email,
                    "pending": True,
                    "type": "internal",
                    "recommended": False,
                }
            elif lawyer.username in dummy_lawyers:
                if lawyer.email not in [
                    *connected_lawyers,
                    *list(pending_lawyers.keys()),
                ]:
                    preRec_dummyLawyers[lawyer.email] = {
                        "Point of Contact": f"{lawyer.full_legal_name}",
                        "Law Firm Name": lawyer.law_firm_name,
                        "Experience": lawyer.experience,
                        "Expertise": lawyer.specialty,
                        "Main Office": lawyer.professional_address,
                        "Phone Number": lawyer.contact_number,
                        "Image link": lawyer.profile_picture,
                        "Email Address": lawyer.email,
                        "pending": False,
                        "type": "internal",
                        "recommended": False,
                    }

        for ext_lawyer in unregistered_lawyers:
            if ext_lawyer.email not in list(invited_external_lawyers.keys()):
                preRec_unregLawyers.append(
                    {
                        "username": ext_lawyer.username,
                        "email": ext_lawyer.email,
                        "full_name": ext_lawyer.fullName,
                        "law_firm": ext_lawyer.lawFirmName,
                        "experience": ext_lawyer.experience,
                        "expertise": ext_lawyer.expertise,
                        "location": ext_lawyer.professionalAddress,
                    }
                )
            else:
                invited_unregLawyers[ext_lawyer.email] = {
                    "Point of Contact": ext_lawyer.fullName,
                    "Law Firm Name": ext_lawyer.lawFirmName,
                    "Experience": ext_lawyer.experience,
                    "Expertise": ext_lawyer.expertise,
                    "Main Office": ext_lawyer.professionalAddress,
                    "Phone Number": ext_lawyer.contactNumber,
                    "Image link": ext_lawyer.profilePicture,
                    "Email Address": ext_lawyer.email,
                    "pending": True,
                    "type": "external",
                    "recommended": False,
                }

        return (
            preRec_regLawyers,
            preRec_unregLawyers,
            preRec_dummyLawyers,
            pending_regLawyers,
            invited_unregLawyers,
            immigrant_data,
        )

    def _gen_recommendation(
        self,
        registered_lawyers: list[dict[str, str]],
        unregistered_lawyers: list[dict[str, str]],
        immigrant: Immigrants = None,
        override_immigrant_data: dict[str, Union[str, EmailStr]] = None
    ) -> dict[str, list[str]]:
        client = OpenAI(api_key=self.OPENAI_API_KEY)
        immigrant_data = override_immigrant_data
        if not override_immigrant_data:
            _, _, _, _, _, immigrant_data = self.presort_lawyers(immigrant)
        username = immigrant_data.get("username")
        if not username:
            return {"registered": [], "unregistered": []}

        non_file_data = self._get_non_file_data(username)
        kyc_data = non_file_data.get("kyc", {})
        messages = non_file_data.get("messages", [])

        rag_query = f"Extract context about user {username}'s legal situation, case type, specific needs, and location relevant for finding a suitable lawyer."
        retrieved_context = rag_app.retrieve_hybrid_context(username, rag_query)

        if retrieved_context is None:
            retrieved_context = ""
        elif not retrieved_context:
            retrieved_context = ""

        tool_name = "provide_lawyer_recommendations"
        recommendation_tool = self._create_tool_from_pydantic(
            GeneratedLawyerRecommendations, tool_name
        )

        system_prompt = generate_recommendation_prompt(
            immigrant_data=immigrant_data,
            retrieved_context=retrieved_context,
            messages=messages,
            registered_lawyers=registered_lawyers,
            unregistered_lawyers=unregistered_lawyers,
            kyc_data=kyc_data,
            tool_name=tool_name,
        )
        user_message = f"Based on my profile, the provided context, and the lawyer lists, please recommend the most suitable registered and unregistered lawyers by calling the '{tool_name}' tool."
        recommendations_dict = {"registered": [], "unregistered": []}
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = client.chat.completions.create(
                    model="gpt-5",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    tools=[recommendation_tool],
                    tool_choice={"type": "function", "function": {"name": tool_name}},
                    reasoning_effort="high"
                )

                message = response.choices[0].message
                finish_reason = response.choices[0].finish_reason

                if finish_reason == 'tool_calls' and message.tool_calls:
                    tool_call = message.tool_calls[0]
                    if tool_call.function.name == tool_name:
                        arguments_str = tool_call.function.arguments
                        try:
                            parsed_args = json.loads(arguments_str)
                            validated_data = GeneratedLawyerRecommendations(
                                **parsed_args
                            )
                            if hasattr(validated_data, "registered"):
                                for item in validated_data.registered:
                                    if item and hasattr(item, "lawyer_email") and item.lawyer_email:
                                        recommendations_dict["registered"].append(
                                            item.lawyer_email
                                        )
                            if hasattr(validated_data, "unregistered"):
                                for item in validated_data.unregistered:
                                    if (
                                        item
                                        and hasattr(item, "lawyer_email")
                                        and item.lawyer_email
                                    ):
                                        recommendations_dict["unregistered"].append(
                                            item.lawyer_email
                                        )

                            return recommendations_dict

                        except json.JSONDecodeError as json_e:
                            print(f"Error: Failed to decode JSON arguments: {json_e}")
                            print(f"Raw arguments: {arguments_str}")
                        except Exception as pydantic_e:
                            print(f"Error: Failed to validate/process tool arguments: {pydantic_e}")
                            if 'parsed_args' in locals():
                                print(f"Parsed arguments causing validation error: {parsed_args}")
                    else:
                        print(f"Warning: Model called unexpected tool '{tool_call.function.name}'.")
                else:
                    print(f"Warning: Model did not make the expected tool call. Finish reason: {finish_reason}")
                    if message.content: print(f"Model response: {message.content[:200]}...")

            except Exception as e:
                print(f"API Error on attempt {attempt + 1}: {e}")

            if attempt < max_attempts - 1:
                wait_time = 3 * (attempt + 1)
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)

        print(f"Error: Failed to get recommendations after {max_attempts} attempts.")
        return recommendations_dict

    def _to_generate(self, preRec: dict[Literal["registered", "unregistered"], list[EmailStr]], prev_rec: dict[Literal["registered", "unregistered"], list[EmailStr]]) -> bool:
        isReg_empty = len(prev_rec["registered"]) == 0 and len(preRec["registered"]) != 0
        isUnreg_empty = len(prev_rec["unregistered"]) == 0 and len(preRec["unregistered"]) != 0
        if isReg_empty or isUnreg_empty:
            return True
        return False

    def check_generated(
        self,
        preRec: dict[Literal["registered", "unregistered"], list[EmailStr]],
        rec: dict[Literal["registered", "unregistered"], list[EmailStr]],
    ) -> bool:
        isReg_same = sorted(preRec["registered"]) == sorted(rec["registered"])
        isUnreg_same = sorted(preRec["unregistered"]) == sorted(rec["unregistered"])
        if isReg_same and isUnreg_same:
            return False
        return True

    def generate(
        self, immigrant_email: EmailStr, force: bool = False
    ) -> None:
        immigrant = db_func.get_immigrant(immigrant_email)
        registered_lawyers, unregistered_lawyers, _, _, _, immigrant_data = self.presort_lawyers(immigrant=immigrant)
        previous_recommendations = db_func.get_lawyer_recommendations(immigrant.email)
        preRec = {
            "registered": [regLawyer["email"] for regLawyer in registered_lawyers],
            "unregistered": [unregLawyer["email"] for unregLawyer in unregistered_lawyers],
        }
        if self._to_generate(preRec, previous_recommendations) or force:
            recOrdered_dictionary = self._gen_recommendation(
                registered_lawyers,
                unregistered_lawyers,
                immigrant=immigrant,
                override_immigrant_data=immigrant_data,
            )
            recOrdered_dictionary["registered"].extend(
                [
                    rec
                    for rec in preRec["registered"]
                    if rec not in recOrdered_dictionary["registered"]
                ]
            )
            recOrdered_dictionary["unregistered"].extend(
                [
                    rec
                    for rec in preRec["unregistered"]
                    if rec not in recOrdered_dictionary["unregistered"]
                ]
            )
            while self.check_generated(preRec, recOrdered_dictionary):
                recOrdered_dictionary = self._gen_recommendation(
                    registered_lawyers, unregistered_lawyers, immigrant_data
                )
                recOrdered_dictionary["registered"].extend(
                    [
                        rec
                        for rec in registered_lawyers
                        if rec not in recOrdered_dictionary["registered"]
                    ]
                )
                recOrdered_dictionary["unregistered"].extend(
                    [
                        rec
                        for rec in unregistered_lawyers
                        if rec not in recOrdered_dictionary["unregistered"]
                    ]
                )
            db_func.update_lawyer_recommendations(
                immigrant_email,
                recOrdered_dictionary["registered"],
                recOrdered_dictionary["unregistered"],
            )
