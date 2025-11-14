import json
from typing import Any, Optional
from openai import OpenAI
import os
from rag_gateway import RAGGateway
from helpers import Helpers
from response_schemas import AutofillResponse
from database import Functions

db_func = Functions()

class AutofillGenerator:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def __init__(self, rag_config_name: str = "balanced"):
        self.rag_app = RAGGateway(config_name=rag_config_name)
        self.supported_forms = Helpers.get_supported_forms()
        self.form_schemas = {}
        self.modular_forms = list(self.form_schemas.keys())

    def _extract_fields(self, form_context: dict[str, Any]) -> dict[str, dict[str, Any]]:
        fields = {}
        if "items" in form_context:
            for item in form_context["items"]:
                field_name = item.get("field_name", "")
                if field_name:
                    fields[field_name] = {
                        "type": item.get("type", "text"),
                        "description": item.get("description", ""),
                        "required": item.get("required", False),
                        "value_spec": item.get("value_spec", {}),
                        "options": item.get("options", [])
                    }
        return fields

    def _load_modular_schema(self, form_name: str) -> Optional[dict[str, Any]]:
        try:
            form_context = Helpers.get_form_context(form_name)
            form_fieldmap = Helpers.get_form_fieldmap(form_name)
            form_analysis = Helpers.get_form_analysis(form_name)
            schema = {
                "form_name": form_name,
                "context": form_context,
                "fieldmap": form_fieldmap,
                "analysis": form_analysis,
                "fields": self._extract_fields(form_context)
            }
            return schema

        except Exception as e:
            return None

    def _load_all_form_schemas(self):
        for form_name in self.supported_forms:
            schema = self._load_modular_schema(form_name)
            if schema:
                self.form_schemas[form_name] = schema

    def _load_modular_field_descriptions(self, form_name: str) -> dict[str, Any]:
        try:
            form_schema = self.form_schemas.get(form_name)
            if form_schema and isinstance(form_schema, dict) and "fields" in form_schema:
                return form_schema["fields"]
            else:
                return {}
        except Exception as e:
            return {}

    def _get_immigrant_context(self, immigrant_username: str, case_type: str = None, context_override: dict[str, Any] = None, limit: int = 50) -> dict[str, Any]:
        if context_override:
            return context_override

        try:
            immigrant = db_func.get_immigrant(immigrant_username)
            kyc_data = db_func.get_immigrant_kyc(immigrant.username)
            messages = Helpers.retreive_ai_messages_for_autofill(db_func.process_immigrant_messages(immigrant_email=immigrant.email), limit)
            case_info = {}
            if case_type:
                case_info = db_func.retrieve_case_info(immigrant.username, case_type)

            return {
                "user_info": {
                    "username": immigrant.username,
                    "email": immigrant.email,
                    "full_legal_name": immigrant.full_legal_name
                },
                "kyc_data": kyc_data or {},
                "messages": messages or {},
                "case_info": case_info,
                "case_type": case_type
            }

        except Exception as e:
            return {}

    def _get_rag_context(self, immigrant_username: str, form_name: str, case_type: str = None, rag_context_override: str = None):
        if rag_context_override:
            return rag_context_override
        try:
            rag_query = f"Extract context about user {immigrant_username}'s personal information, immigration history, case details"
            if case_type:
                rag_query += f", {case_type} case information"
            rag_query += f", and information relevant for filling out form {form_name}"
            context = self.rag_app.retrieve_hybrid_context(
                username=immigrant_username,
                query=rag_query,
                file_urls=None,
                top_k_files=8,
                top_k_general=5,
            )

            return context if context else ""

        except Exception as e:
            return ""
    def _create_autofill_prompt(
        self,
        form_name: str,
        field_descriptions: dict[str, Any],
        user_context: dict[str, Any],
        rag_context: str
    ) -> str:
        return f"""You are an expert immigration form assistant that generates accurate autofill data for USCIS forms.

            **Your Task**: Generate autofill data for form {form_name.upper()} based on the provided user context.

            **Form Information**:
            - Form: {form_name.upper()}
            - Field Descriptions: {json.dumps(field_descriptions, indent=2) if field_descriptions else "No field descriptions available"}

            **User Context**:
            {json.dumps(user_context, indent=2)}

            **Retrieved Document Context**:
            {rag_context}

            **Instructions**:
            1. Analyze the user context and document context to extract relevant information
            2. Map the extracted information to appropriate form fields
            3. Only include fields where you have confident, accurate information
            4. For dates, use MM/DD/YYYY format
            5. For yes/no questions, use "yes" or "no" (lowercase)
            6. For multiple choice fields, use exact option values
            7. Ensure all information is consistent across related fields
            8. Do not fabricate or guess information - only use what's clearly available

            **Response Format**:
            Return a JSON object with field names as keys and their values. Example:
            {{
                "field_name": "value",
                "date_field": "12/31/2023",
                "yes_no_field": "yes",
                "multiple_choice_field": "option_value"
            }}

            **Quality Guidelines**:
            - Accuracy is more important than completeness
            - Cross-reference information across different sources
            - Maintain consistency in names, dates, and addresses
            - Follow USCIS formatting requirements
        """

    def _generate_form_data(
        self,
        form_name: str,
        field_descriptions: dict[str, Any],
        user_context: dict[str, Any],
        rag_context: str,
    ) -> dict[str, Any]:
        try:
            system_prompt = self._create_autofill_prompt(
                form_name=form_name,
                field_descriptions=field_descriptions,
                user_context=user_context,
                rag_context=rag_context,
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Generate autofill data for form {form_name} based on the provided context.",
                },
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-5",
                messages=messages,
                response_format={"type": "json_object"},
                reasoning_effort="high"
            )

            response_content = response.choices[0].message.content
            parsed_data = json.loads(response_content)

            return parsed_data

        except Exception as e:
            return {}

    def _validate_and_filter_data(
            self,
            data: dict[str, Any],
    ) -> dict[str, Any]:
        filtered_data = {}
        for field_name, value in data.items():
            if not value or (isinstance(value, str) and len(value.strip()) == 0):
                continue

            if isinstance(value, list) and (
                len(value) == 0 or not any(str(item).strip() for item in value)
            ):
                continue

            if isinstance(value, (str, int, float, bool)) or (
                isinstance(value, list) and len(value) > 0
            ):
                filtered_data[field_name] = value

        return filtered_data

    def generate(self, immigrant_username: str, form_name: str, case_type: str = None, context_override: dict[str, Any] = None, rag_context_override: str = None):
        try:
            if form_name not in self.supported_forms:
                return AutofillResponse(
                    success=False,
                    message=f"Error: Form type '{form_name}' is not supported. Supported forms: {', '.join(self.supported_forms)}",
                    autofill_data={},
                )
            form_schema = self.form_schemas.get(form_name)
            if not form_schema:
                return AutofillResponse(
                    success=False,
                    message=f"Error: Form schema for '{form_name}' is not available",
                    autofill_data={},
                )

            form_descriptions = {}
            if form_name in self.modular_forms:
                form_descriptions = self._load_modular_field_descriptions(form_name)

            immigrant_context = self._get_immigrant_context(immigrant_username=immigrant_username, case_type=case_type, context_override=context_override, limit=50)
            immigrant_rag_context = self._get_rag_context(immigrant_username=immigrant_username, form_name=form_name, case_type=case_type, context_override=rag_context_override)
            autofill_data = self._generate_form_data(
                form_name=form_name,
                field_descriptions=form_descriptions,
                user_context=immigrant_context,
                rag_context=immigrant_rag_context
            )

            filtered_data = self._validate_and_filter_data(autofill_data)
            db_func.update_autofill_data(immigrant_username=immigrant_username, form_name=form_name, field_descriptions=form_descriptions, immigrant_context=immigrant_context, immigrant_rag_context=immigrant_rag_context, autofill_data=filtered_data)
            return AutofillResponse(
                success=True,
                message=f"Autofill data generated successfully for form {form_name}.",
                autofill_data=filtered_data,
                form_name=form_name,
                generated_field_count=len(filtered_data)
            )

        except Exception as e:
            return AutofillResponse(
                success=False,
                message="Sorry, a critical error occured while generating autofill data, please try again later",
                autofill_data={}
            )
