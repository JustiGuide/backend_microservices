import base64
import io
import json
import os
from typing import Any
from openai import OpenAI
from pdf2image import convert_from_path, convert_from_bytes
from dotenv import load_dotenv

load_dotenv()

class SignaturePositionLocatorApplication:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    DEFAULT_DPI = 300
    HIGH_DPI = 600

    def __init__(self):
        self.SIGNATURE_EXTRACTION_PROMPT = self._get_signature_extraction_prompt()

    def _get_signature_extraction_prompt(self) -> str:
        return """
        **System Prompt for PDF Signature Extraction Assistant**

        **Your Role:**
        You are an AI assistant specialized in document analysis for signature placement. Your primary goal is to analyze PDF documents and identify all locations where a signature is required. For each such location, you must extract two key pieces of information:
        1. The **page number** (1-indexed) where the signature is to be placed.
        2. The **Y and X offset percentages** (ranging from 0.00 to 1.00). These percentages, referred to as `offset_y_factor` and `offset_x_factor` respectively, determine the placement of the top-left corner of a scaled signature image on that page.

        **Mathematical Formulas for Offset Calculation:**
        The offset factors must be calculated using these precise formulas:
        1. `offset_y_factor = Y_placement_coordinate_pixels / (page_height_pixels - scaled_signature_height_pixels)`
        2. `offset_x_factor = X_placement_coordinate_pixels / (page_width_pixels - scaled_signature_width_pixels)`

        Where:
        * `(X_placement_coordinate_pixels, Y_placement_coordinate_pixels)` is the target top-left pixel coordinate for placing the *scaled* signature image on the page. The origin (0,0) is the top-left corner of the page.
        * `page_width_pixels` and `page_height_pixels` are the dimensions of the current PDF page in pixels.
        * `scaled_signature_width_pixels = page_width_pixels / 5` (signature width is 1/5th of page width)
        * `scaled_signature_height_pixels` is calculated maintaining aspect ratio of the signature
        * If denominators are zero or negative, the corresponding offset should be 0.

        **Your Detailed Task:**
        1. Carefully examine each page of the provided PDF document.
        2. Identify all distinct locations intended for a signature. Look for:
           * Explicit text cues such as "Signature," "Applicant's Signature," "Petitioner's Signature," "Client Signature," "Sign Here," "Your Signature."
           * Designated signature lines.
           * Empty rectangular boxes clearly intended for signatures.
           * Often, these are found near "Date" fields or at the end of sections/forms.
           * **Prioritize locations clearly designated for the primary individual (client, applicant, petitioner) whose signature is the main purpose of the document.**
        3. For each identified signature location:
           a. Determine the `page_number` (1-indexed).
           b. Visually determine the most appropriate `(X_placement_coordinate_pixels, Y_placement_coordinate_pixels)` on the page for the top-left corner of the *scaled* signature image. The signature should be placed naturally and aesthetically:
              * Typically, the baseline of the signature text should align with the provided signature line.
              * It should fit reasonably within any designated box.
              * It must not obscure other important text or elements on the page.
              * Remember that the scaled signature's width will be 1/5th of the page width.
           c. Using these determined placement coordinates and the page/scaled signature dimensions, calculate the `offset_y_factor` and `offset_x_factor` using the formulas provided above. Ensure the values are between 0.00 and 1.00.

        **Output Format:**
        You MUST return the results **only** as a valid JSON list of objects. Do NOT include any explanatory text, reasoning, conversational remarks, or any characters before or after the JSON list. Your entire response should be parsable as JSON. Each object represents a unique signature location and must follow this structure precisely:
        ```json
        [
        {
            "page_number": <integer>,
            "offsets": [<float_y_offset_factor>, <float_x_offset_factor>]
        },
        {
            "page_number": <integer>, 
            "offsets": [<float_y_offset_factor>, <float_x_offset_factor>]
        }
        ]
        ```
        If no signature locations are found in the entire document, return an empty JSON list: `[]`.

        **Important Considerations:**
        * **Multiple Signatures on a Single Page:** If a page contains multiple, distinct signature fields that would necessitate different placement coordinates, generate a separate JSON object for each.
        * **Accuracy of Placement:** The core of your visual task is to determine the `(X_placement_coordinate_pixels, Y_placement_coordinate_pixels)` that represents a natural and correct placement for the signature.
        * **Handling Ambiguity:** If a signature location is highly ambiguous or seems to be missing a clear line/box, use your best judgment to identify the most probable location.
        * **Strict Adherence to Formulas:** The final `offset_y_factor` and `offset_x_factor` MUST be calculated using the provided formulas.
        """

    async def _pdf_file_to_base64_images(
        self, pdf_file_path: str, dpi: int = None
    ) -> list[str]:
        if dpi is None:
            dpi = self.DEFAULT_DPI

        if not os.path.exists(pdf_file_path):
            raise FileNotFoundError(f"PDF file not found at {pdf_file_path}")

        base64_images = []
        try:
            pil_images = convert_from_path(pdf_file_path, dpi=dpi)

            for i, pil_image in enumerate(pil_images):
                buffered = io.BytesIO()
                pil_image.save(buffered, format="PNG")
                img_bytes = buffered.getvalue()

                base64_image = base64.b64encode(img_bytes).decode("utf-8")
                base64_images.append(base64_image)
                print(f"Converted page {i + 1} of {pdf_file_path} to image.")

        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            if "poppler" in str(e).lower():
                print(
                    "Poppler not found. Please install Poppler and add it to your PATH."
                )
                print("See pdf2image documentation for installation instructions.")
            raise

        return base64_images

    async def _pdf_bytes_to_base64_images(
        self, pdf_bytes: bytes, dpi: int = None
    ) -> list[str]:
        """Convert PDF bytes to base64 encoded images"""
        if dpi is None:
            dpi = self.DEFAULT_DPI

        base64_images = []
        try:
            pil_images = convert_from_bytes(pdf_bytes, dpi=dpi)

            for i, pil_image in enumerate(pil_images):
                buffered = io.BytesIO()
                pil_image.save(buffered, format="PNG")
                img_bytes = buffered.getvalue()

                base64_image = base64.b64encode(img_bytes).decode("utf-8")
                base64_images.append(base64_image)
                print(f"Converted page {i + 1} from bytes to image.")

        except Exception as e:
            print(f"Error converting PDF bytes to images: {e}")
            if "poppler" in str(e).lower():
                print(
                    "Poppler not found. Please install Poppler and add it to your PATH."
                )
            raise

        return base64_images

    async def _analyze_pdf_for_signatures(
        self, pdf_bytes: bytes
    ) -> list[dict[str, Any]]:
        """Analyze PDF bytes for signature positions"""
        try:
            base64_images = await self._pdf_bytes_to_base64_images(
                pdf_bytes, self.HIGH_DPI
            )

            if not base64_images:
                print("No images could be extracted from the PDF.")
                return []

            return await self._analyze_images_for_signatures(base64_images)

        except Exception as e:
            print(f"Error analyzing PDF for signatures: {e}")
            raise

    async def _analyze_pdf_file_for_signatures(
        self, pdf_file_path: str
    ) -> list[dict[str, Any]]:
        """Analyze PDF file for signature positions"""
        try:
            base64_images = await self._pdf_file_to_base64_images(
                pdf_file_path, self.HIGH_DPI
            )

            if not base64_images:
                print("No images could be extracted from the PDF.")
                return []

            return await self._analyze_images_for_signatures(base64_images)

        except Exception as e:
            print(f"Error analyzing PDF file for signatures: {e}")
            raise

    async def _analyze_images_for_signatures(
        self, base64_images: list[str]
    ) -> list[dict[str, Any]]:
        """Use AI to analyze images and identify signature positions"""
        try:
            messages_content = [
                {
                    "type": "text",
                    "text": "Analyze the following document images to find client signature locations based on the system prompt instructions. Provide the output strictly in the specified JSON format.",
                }
            ]

            for i, b64_img in enumerate(base64_images):
                messages_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64_img}",
                            "detail": "high",
                        },
                    }
                )
                print(f"Added image for page {i+1} to AI analysis request.")

            messages = [
                {"role": "system", "content": self.SIGNATURE_EXTRACTION_PROMPT},
                {"role": "user", "content": messages_content},
            ]

            print("Sending request to OpenAI API for signature analysis...")
            response = self.openai_client.chat.completions.create(
                model="gpt-5",
                messages=messages,
            )

            response_content = response.choices[0].message.content
            print("Received response from OpenAI API.")

            # Clean up response content
            if response_content.strip().startswith("```json"):
                response_content = response_content.strip()[7:]
            if response_content.strip().endswith("```"):
                response_content = response_content.strip()[:-3]

            response_content = response_content.strip()

            try:
                signature_data = json.loads(response_content)
                if not isinstance(signature_data, list):
                    print(
                        f"API response was not a JSON list as expected. Response: {response_content}"
                    )
                    return []

                print(f"Successfully parsed signature data: {signature_data}")
                return signature_data

            except json.JSONDecodeError as je:
                print(f"Failed to decode JSON response from OpenAI: {je}")
                print(f"Problematic response content: {response_content}")
                return []

        except Exception as e:
            print(f"Error in AI signature analysis: {e}")
            raise

    async def _validate_signature_placement(
        self, pdf_bytes: bytes, file_path: str, proposed_positions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Validate proposed signature placements"""
        try:
            # Get current signature positions using AI
            if pdf_bytes:
                ai_positions = await self._analyze_pdf_for_signatures(pdf_bytes)
            elif file_path:
                ai_positions = await self._analyze_pdf_file_for_signatures(file_path)
            else:
                raise ValueError("Either pdf_bytes or file_path must be provided")

            validation_results = []

            for proposed in proposed_positions:
                page_num = proposed.get("page_number")
                offsets = proposed.get("offsets", [])

                # Find AI-suggested positions for this page
                ai_suggestions = [
                    pos for pos in ai_positions if pos.get("page_number") == page_num
                ]

                if not ai_suggestions:
                    validation_results.append(
                        {
                            "page_number": page_num,
                            "valid": False,
                            "reason": "No signature location detected on this page by AI analysis",
                            "proposed_offsets": offsets,
                            "ai_suggestions": [],
                        }
                    )
                    continue

                # Check if proposed position is close to AI suggestions
                is_valid = False
                closest_suggestion = None
                min_distance = float("inf")

                for ai_pos in ai_suggestions:
                    ai_offsets = ai_pos.get("offsets", [])
                    if len(ai_offsets) >= 2 and len(offsets) >= 2:
                        # Calculate Euclidean distance
                        distance = (
                            (offsets[0] - ai_offsets[0]) ** 2
                            + (offsets[1] - ai_offsets[1]) ** 2
                        ) ** 0.5
                        if distance < min_distance:
                            min_distance = distance
                            closest_suggestion = ai_pos

                        # Consider valid if within reasonable distance (0.1 = 10% of page)
                        if distance < 0.1:
                            is_valid = True

                validation_results.append(
                    {
                        "page_number": page_num,
                        "valid": is_valid,
                        "distance_to_nearest": min_distance,
                        "proposed_offsets": offsets,
                        "closest_ai_suggestion": closest_suggestion,
                        "all_ai_suggestions": ai_suggestions,
                    }
                )

            return {
                "overall_valid": all(result["valid"] for result in validation_results),
                "validation_details": validation_results,
                "ai_detected_positions": ai_positions,
            }

        except Exception as e:
            print(f"Error validating signature placement: {e}")
            raise
