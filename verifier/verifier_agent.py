import base64
import logging
import os
from typing import Dict, List, Union, Tuple, Optional
from pydantic import BaseModel, Field, EmailStr
from openai import OpenAI
from rapidfuzz import fuzz
from dotenv import load_dotenv

load_dotenv()

class LawPersonnelVerifier:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    MAX_RETRIES = 3
    MIN_NAME_SIMILARITY = 85
    file_data = {
        "government_id": ["Full Legal Name", "Date of Birth", "ID Type"],
        "professional_license": ["Full Legal Name", "Bar ID", "State"],
        "address_proof": ["Full Legal Name", "State"],
    }

    data_template = {
        "full_legal_name": "N/A",
        "date_of_birth": "N/A",
        "id_type": "N/A",
        "state": "N/A",
        "bar_id": "N/A",
    }

    requirements = {
        "government_id": (
            "Visually check for: "
            "1. A Photograph of the individual's face. "
            "2. Individual's Full Name clearly printed. "
            "3. Date of Birth (DOB) clearly visible. "
            "4. A visible unique Identification Number (e.g., Driver's License #, Passport #). "
            "5. Visible Date of Issuance and/or Expiration Date. (Not required for all IDs, but common in many government-issued IDs)"
        ),
        "professional_license": (
            "Visually check for: "
            "1. Lawyer's Full Name clearly printed. "
            "2. A visible License or Registration Number. "
            "3. State of Practice clearly indicated. (e.g., 'The State Bar of California', 'New York State Bar', etc.)"
        ),
        "address_proof": (
            "Visually check for: "
            "1. Individual's Full Name clearly printed. "
            "2. A complete Current Residential Address. "
            "3. Clear indication of Document Type (e.g., 'Utility Bill', 'Bank Statement', 'Lease Agreement', 'Tax Document'). "
            "4. Recognizable official Letterhead, Logo, or Name of the issuing organization (e.g., utility company, bank, government agency). "
            "5. A visible Date of Issuance or Statement Date."
        ),
    }

    def _ocr_agent(self, file_type: str, file_bytes: bytes) -> Dict[str, str]:
        try:
            data_to_extract = ", ".join(self.file_data[file_type])
            base64_image = base64.b64encode(file_bytes).decode("utf-8")

            prompt = f"""
            You are an expert OCR agent. Analyze the provided image of a '{' '.join(word.capitalize() for word in file_type.split('_'))}'.
            Extract the following fields: {data_to_extract}.
            If a field is not found, set its value to an empty string "".
            Some notes:
            - The Bar ID is the unique identifier for a lawyer's license, typically issued by the state bar association, and is typically a 6-digit number. It can have a symbol before or after the number (#, No., etc.)
            - The document can be a scanned image or a photo, and may contain noise or artifacts.
            - Extract Full Legal Name, it may be in various formats (e.g., "John Doe", "Doe, John") and it could be divided into first name and last name, combine them into a single string.
            - Extract Date of Birth in the format "YYYY-MM-DD" (e.g., "2025-06-25").
            """

            response = self.openai_client.beta.chat.completions.parse(
                model="gpt-5",
                response_format=OcrDataResponse,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                                "detail": "high"
                            },
                        ],
                    }
                ],
            )

            parsed_data = response.choices[0].message.parsed
            return {
                "full_legal_name": parsed_data.full_legal_name,
                "date_of_birth": parsed_data.date_of_birth,
                "id_type": parsed_data.id_type,
                "state": parsed_data.state,
                "bar_id": parsed_data.bar_id,
            }

        except Exception as e:
            return {}

    def _file_validation(self, file_type: str, file_bytes: bytes) -> bool:
        try:
            base64_image = base64.b64encode(file_bytes).decode("utf-8")

            prompt = f"""
            You are a forensic document validation expert. Analyze the provided image of a document claiming to be a '{' '.join(word.capitalize() for word in file_type.split('_'))}'.
            Perform these checks:
            1. **Authenticity Check**: Does this look like a real {' '.join(word.capitalize() for word in file_type.split('_'))}? Assess layout, fonts, and expected official markings. Here are some additional requirements for a validity check. Strictly check ONLY for the visual presence of these elements: {self.requirements[file_type]}. Do not infer or assume information not visually present.
            2. **Integrity Check**: Are there signs of digital manipulation or tampering?
            3. **Content Check**: Does it contain the kind of data fields one would expect, such as '{', '.join(self.file_data[file_type])}'?
            Some notes:
            - The Bar ID is the unique identifier for a lawyer's license, typically issued by the state bar association, and is typically a 6-digit number. It can have a symbol before or after the number (#, No., etc.).
            - The document can be a scanned image or a photo, and may contain noise or artifacts
            - A signature is not required for this validation.
            """

            response = self.openai_client.beta.chat.completions.parse(
                model="gpt-5",
                response_format=FileValidationResponse,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                                "detail": "high",
                            },
                        ],
                    }
                ],
            )

            validation_result = response.choices[0].message.parsed

            if not validation_result.is_valid:
                self.failures = validation_result.failures or ["AI validation failed."]
                return False

            return True

        except Exception as e:
            self.failures = [f"File validation agent failed for {file_type}: {e}"]
            return False

    def _validate_bar_id(self, bar_id: str, state: str, full_legal_name: str) -> bool:
        """Validate bar ID using AI knowledge base"""
        try:
            if not all([bar_id, state, full_legal_name]):
                self.failures = [
                    "Cannot validate bar ID: Missing Bar ID, State, or Full Legal Name."
                ]
                return False

            analysis_prompt = f"""
            You are a legal verification assistant. Access your internal knowledge base to verify if a lawyer named "{full_legal_name}" is associated with the Bar ID "{bar_id}" in the state of "{state}".
            Acknowledge that your data is not real-time and base your conclusion on the information present in your training data.
            """

            response = self.openai_client.beta.chat.completions.parse(
                model="gpt-5",
                response_format=BarIdValidationResponse,
                messages=[{"role": "user", "content": analysis_prompt}],
            )

            analysis_result = response.choices[0].message.parsed

            if not analysis_result.is_valid:
                self.failures = [
                    analysis_result.reason
                    or "AI could not validate the Bar ID from its internal knowledge."
                ]
                return False

            return True

        except Exception as e:
            return False

    def _extract_data(
        self, file_bytes: Dict[str, bytes]
    ) -> Dict[str, Union[str, bool]]:
        data_template = self.data_template.copy()

        for file_type, file_content in file_bytes.items():
            extracted_data = self._ocr_agent(file_type, file_content)

            for key, value in extracted_data.items():
                if key in data_template and value not in (None, "", "N/A"):
                    data_template[key] = value

        return data_template

    def _single_file_validation(
        self,
        file_type: str,
        file_bytes: bytes,
        extracted_data: Dict[str, Union[str, bool]],
        provided_data: Dict[str, str],
    ) -> bool:
        self.failures = []

        if not self._file_validation(file_type, file_bytes):
            return False

        if file_type == "professional_license":
            bar_id = extracted_data.get("bar_id", "")
            state = extracted_data.get("state", "")
            full_name = extracted_data.get("full_legal_name", "")

            if bar_id and state and full_name:
                if not self._validate_bar_id(bar_id, state, full_name):
                    return False

        data_check = True
        for key, expected_value in provided_data.items():
            relevant_keys = [
                k.lower().replace(" ", "_") for k in self.file_data[file_type]
            ]

            if key in relevant_keys:
                ocr_value = extracted_data.get(key, "")

                if key == "full_legal_name":
                    similarity = fuzz.token_set_ratio(
                        expected_value.lower(), ocr_value.lower()
                    )
                    if similarity < self.MIN_NAME_SIMILARITY:
                        data_check = False
                        self.failures.append(
                            f"Data mismatch for {key}. Expected '{expected_value}', but OCR found '{ocr_value}' (Similarity: {similarity}%)."
                        )
                        break
                else:
                    if ocr_value != expected_value:
                        data_check = False
                        self.failures.append(
                            f"Data mismatch for {key}. Expected '{expected_value}', but OCR found '{ocr_value}'."
                        )
                        break

        return data_check

    def _run_verification(
        self, file_bytes: Dict[str, bytes], provided_data: Dict[str, str]
    ) -> Tuple[bool, Optional[List[str]]]:
        """Run complete verification process with retries"""
        final_failures = []
        overall_success = True

        # Extract data from all documents
        extracted_data = self._extract_data(file_bytes)

        # Validate each document
        for file_type, bytes_data in file_bytes.items():
            success = False

            for attempt in range(self.MAX_RETRIES):
                if self._single_file_validation(
                    file_type, bytes_data, extracted_data, provided_data
                ):
                    success = True
                    self.failures = []
                    break

            if not success:
                final_failures.extend(self.failures)
                overall_success = False

        if overall_success:
            return True, None
        else:
            return False, list(set(final_failures))

class DocumentVerificationRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of the law personnel")
    personnel_type: str = Field(
        ..., description="Type of personnel: lawyer, paralegal, nonlawyer, lawstudent"
    )
    file_bytes: Dict[str, str] = Field(
        ..., description="Dictionary of file types to base64 encoded bytes"
    )
    provided_data: Dict[str, str] = Field(
        ..., description="User provided data for cross-validation"
    )


class DocumentExtractionRequest(BaseModel):
    file_bytes: Dict[str, str] = Field(
        ..., description="Dictionary of file types to base64 encoded bytes"
    )


class SingleDocumentValidationRequest(BaseModel):
    file_type: str = Field(..., description="Type of document to validate")
    file_bytes: str = Field(..., description="Base64 encoded document bytes")


class OcrDataResponse(BaseModel):
    full_legal_name: str = Field(
        "", description="The full legal name of the individual"
    )
    date_of_birth: str = Field("", description="The date of birth of the individual")
    id_type: str = Field("", description="The type of the identification document")
    state: str = Field("", description="The state of residence")
    bar_id: str = Field("", description="The bar ID of the legal professional")


class FileValidationResponse(BaseModel):
    is_valid: bool = Field(..., description="Whether the document is valid or not")
    failures: List[str] = Field(
        default_factory=list,
        description="A list of reasons why the document is not valid",
    )


class BarIdValidationResponse(BaseModel):
    is_valid: bool = Field(..., description="Whether the bar ID is valid or not")
    reason: str = Field(..., description="The reason for the validation result")
