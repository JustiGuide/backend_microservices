import cv2
import numpy as np
import os
import PyPDF2
from pdf2image import convert_from_path
from pydantic import EmailStr
from reportlab.pdfgen import canvas
import glob
import base64
from typing import Dict, Tuple
import fitz
from database import Functions, LawPersonnel
from signature_processing.sign_processing import SignGenerator

db_func = Functions()
signer = SignGenerator()

class FormFiller:
    independent_cases = ["n400"]
    def find_widget_by_name(
        self, doc: fitz.Document, field_name: str
    ) -> Tuple[fitz.Page, fitz.Widget]:
        for page in doc:
            for widget in page.widgets():
                if widget.field_name == field_name:
                    return page, widget
        return None, None

    def sign_pdf(self, input_path, output_path, user_email, full_legal_name, sign_data):

        temp_path = "./temp_formfiller_pages"
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)

        file_name_base = os.path.splitext(os.path.basename(input_path))[0]

        with open(input_path, "rb") as f_in:
            pdf_reader = PyPDF2.PdfReader(f_in)
            if not pdf_reader.pages:
                print(f"Error: No pages found in {input_path}")
                for f_item in glob.glob(os.path.join(temp_path, "*")):
                    os.remove(f_item)
                if os.path.exists(temp_path) and not os.listdir(temp_path):
                    os.rmdir(temp_path)
                return None, None

            first_page_for_dims = pdf_reader.pages[0]
            page_width_pt = float(first_page_for_dims.mediabox.width)
            page_height_pt = float(first_page_for_dims.mediabox.height)

            for i, page_obj in enumerate(pdf_reader.pages):
                writer = PyPDF2.PdfWriter()
                writer.add_page(page_obj)
                temp_pdf_page_path = os.path.join(
                    temp_path, f"{file_name_base}_page_{i}.pdf"
                )
                with open(temp_pdf_page_path, "wb") as f_out_page:
                    writer.write(f_out_page)

        for sig_data in sign_data:
            sign_response = signer.retrieve_signs(
                user_email, sig_data["sign_id"], full_legal_name
            )[0]
            if not sign_response or "sign_b64" not in sign_response:
                return None

            img_data = signer.get_sign_Image(sign_response["sign_b64"])
            user_sign_rgba_np = np.array(img_data)
            target_page_num = sig_data["target_page"]
            offset_factors = sig_data["offset_factors"]

            if user_sign_rgba_np.ndim != 3 or user_sign_rgba_np.shape[2] != 4:
                print(
                    f"Warning: Signature for page {target_page_num} is not a valid RGBA image. Skipping."
                )
                continue

            original_sig_height, original_sig_width = user_sign_rgba_np.shape[:2]
            if original_sig_height == 0 or original_sig_width == 0:
                print(
                    f"Warning: Signature for page {target_page_num} has zero dimensions. Skipping."
                )
                continue

            page_to_sign_idx = target_page_num - 1
            temp_pdf_to_sign_path = os.path.join(
                temp_path, f"{file_name_base}_page_{page_to_sign_idx}.pdf"
            )
            temp_jpg_page_path = os.path.join(
                temp_path, f"{file_name_base}_page_{page_to_sign_idx}.jpg"
            )

            if not os.path.exists(temp_pdf_to_sign_path):
                print(
                    f"Warning: Page PDF {temp_pdf_to_sign_path} not found for signature. Skipping."
                )
                continue

            try:
                page_images = convert_from_path(temp_pdf_to_sign_path, dpi=600)
                if not page_images:
                    print(
                        f"Warning: Could not convert page {temp_pdf_to_sign_path} to image. Skipping."
                    )
                    continue
                page_images[0].save(temp_jpg_page_path, "JPEG")
            except Exception as e:
                print(
                    f"Error converting PDF page to JPG: {e}. Skipping signature on this page."
                )
                continue

            cv_page_bgr = cv2.imread(temp_jpg_page_path)
            if cv_page_bgr is None:
                print(
                    f"Warning: Could not read page image {temp_jpg_page_path} with OpenCV. Skipping."
                )
                continue

            page_img_height, page_img_width = cv_page_bgr.shape[:2]
            original_sig_rgb = user_sign_rgba_np[:, :, :3]
            alpha_channel = user_sign_rgba_np[:, :, 3]
            original_sig_bgr = cv2.cvtColor(original_sig_rgb, cv2.COLOR_RGB2BGR)
            target_sig_width_on_page = page_img_width / 5.0
            scale_factor = target_sig_width_on_page / original_sig_width

            scaled_sig_width = int(original_sig_width * scale_factor)
            scaled_sig_height = int(original_sig_height * scale_factor)

            if scaled_sig_width <= 0 or scaled_sig_height <= 0:
                print(
                    f"Warning: Scaled signature for page {target_page_num} has zero/negative dimensions. Skipping."
                )
                continue

            scaled_sig_bgr_color = cv2.resize(
                original_sig_bgr,
                (scaled_sig_width, scaled_sig_height),
                interpolation=cv2.INTER_AREA,
            )
            scaled_alpha_mask = cv2.resize(
                alpha_channel,
                (scaled_sig_width, scaled_sig_height),
                interpolation=cv2.INTER_NEAREST,
            )
            offset_y_factor, offset_x_factor = offset_factors[0], offset_factors[1]

            available_y_for_offset = page_img_height - scaled_sig_height
            available_x_for_offset = page_img_width - scaled_sig_width

            pos_y = (
                int(available_y_for_offset * offset_y_factor)
                if available_y_for_offset > 0
                else 0
            )
            pos_x = (
                int(available_x_for_offset * offset_x_factor)
                if available_x_for_offset > 0
                else 0
            )

            pos_y = max(0, min(pos_y, page_img_height - scaled_sig_height))
            pos_x = max(0, min(pos_x, page_img_width - scaled_sig_width))

            y1, y2 = pos_y, pos_y + scaled_sig_height
            x1, x2 = pos_x, pos_x + scaled_sig_width

            roi = cv_page_bgr[y1:y2, x1:x2]

            alpha_mask_3channel = cv2.cvtColor(scaled_alpha_mask, cv2.COLOR_GRAY2BGR)

            alpha_float = alpha_mask_3channel.astype(float) / 255.0

            foreground_float = scaled_sig_bgr_color.astype(float)
            background_float = roi.astype(float)

            blended_roi_float = cv2.multiply(
                alpha_float, foreground_float
            ) + cv2.multiply(1.0 - alpha_float, background_float)

            cv_page_bgr[y1:y2, x1:x2] = blended_roi_float.astype(np.uint8)

            cv2.imwrite(temp_jpg_page_path, cv_page_bgr)

            c = canvas.Canvas(
                temp_pdf_to_sign_path, pagesize=(page_width_pt, page_height_pt)
            )
            c.drawImage(
                temp_jpg_page_path, 0, 0, width=page_width_pt, height=page_height_pt
            )
            c.save()

        output_pdf_writer = PyPDF2.PdfWriter()
        num_pages_in_original = 0
        with open(input_path, "rb") as f_orig_count:
            num_pages_in_original = len(PyPDF2.PdfReader(f_orig_count).pages)

        for i in range(num_pages_in_original):
            processed_page_path = os.path.join(
                temp_path, f"{file_name_base}_page_{i}.pdf"
            )
            if os.path.exists(processed_page_path):
                with open(processed_page_path, "rb") as f_page_processed:
                    page_reader = PyPDF2.PdfReader(f_page_processed)
                    if page_reader.pages:
                        output_pdf_writer.add_page(page_reader.pages[0])
                    else:
                        print(
                            f"Warning: Processed page {processed_page_path} is empty or corrupted."
                        )
            else:
                print(
                    f"Warning: Processed page PDF {processed_page_path} not found. Attempting to use original page {i+1}."
                )
                with open(input_path, "rb") as f_original_pdf_for_missing:
                    original_reader_for_missing = PyPDF2.PdfReader(
                        f_original_pdf_for_missing
                    )
                    if i < len(original_reader_for_missing.pages):
                        output_pdf_writer.add_page(original_reader_for_missing.pages[i])

        with open(output_path, "wb") as f_final_out:
            output_pdf_writer.write(f_final_out)

        return output_path, str(output_path).split("/")[-1]

    def fill_form(
        self,
        formname: str,
        data_dict: Dict[str, str],
        user_email: str,
        full_legal_name: str,
        output_filename: str = None,
        is_signer: bool = False,
        lawyer: LawPersonnel = None,
    ):
        formname = formname.lower()
        template_pdf = f"./form_templates/{formname}/{formname}_template.pdf"
        if output_filename.endswith(".pdf"):
            output_filename = output_filename.removesuffix(".pdf")

        output_pdf = f"{formname}_filled"
        if output_filename:
            output_pdf = output_filename

        doc = fitz.open(template_pdf)

        for field_name, value in data_dict.items():
            page, widget = self.find_widget_by_name(doc, field_name)
            if not widget:
                continue

            field_type = field_name.rsplit(".", 1)[-1]

            if field_type in ("text", "textbox"):
                widget.field_value = value
                widget.update()
            elif field_type in ("radio", "checkbox"):
                widget.field_value = True
                widget.update()
            elif field_type == "sign" and is_signer:
                sign_id = value
                if lawyer and field_name.lower().startswith(
                    tuple(["preparer", "attorney", "lawyer"])
                ):
                    sign_response = signer.retrieve_signs(
                        lawyer.email, sign_id, lawyer.full_legal_name
                    )
                else:
                    sign_response = signer.retrieve_signs(
                        user_email, sign_id, full_legal_name
                    )
                if not sign_response or "sign_b64" not in sign_response[0]:
                    continue

                img_data = base64.b64decode(sign_response[0]["sign_b64"])
                field_rect = widget.rect

                aspect_ratio = 500 / 420
                new_h = field_rect.height * 4.5
                new_w = new_h * aspect_ratio

                center_x = field_rect.x0 + field_rect.width / 2
                center_y = field_rect.y0 + field_rect.height / 2

                img_rect = fitz.Rect(
                    center_x - new_w / 2,
                    center_y - new_h / 2,
                    center_x + new_w / 2,
                    center_y + new_h / 2,
                )

                page.insert_image(img_rect, stream=img_data)

        flattened_doc = fitz.open()

        for page in doc:
            pix = page.get_pixmap(dpi=600)
            new_page = flattened_doc.new_page(
                width=page.rect.width, height=page.rect.height
            )
            new_page.insert_image(page.rect, pixmap=pix)

        doc.close()

        # flattened_doc.save(output_pdf, garbage=4, deflate=True, clean=True)
        pdf_bytes = flattened_doc.tobytes(garbage=4, deflate=True, clean=True)
        flattened_doc.close()
        return pdf_bytes, output_pdf

    def is_sign_id(self, data_dict: Dict[str, str], check_lawyer: bool = False) -> bool:
        is_applicant_sign = False
        is_lawyer_sign = False
        for key in data_dict:
            if key.lower().endswith("sign"):
                # Check for lawyer signatures first (more specific)
                if key.lower().startswith(tuple(["attorney", "lawyer", "preparer"])):
                    is_lawyer_sign = True
                # Check for applicant/petitioner signatures (exclude preparer)
                elif key.lower().startswith(
                    tuple(["applicant", "petitioner", "beneficiary"])
                ):
                    is_applicant_sign = True
        if check_lawyer:
            return is_applicant_sign and is_lawyer_sign
        return is_applicant_sign

    def retrieve_all_immigrant_forms(
        self, immigrant_email: EmailStr
    ) -> dict[str, dict]:
        all_form_names = db_func.get_all_formnames()
        form_details = {form_name: {} for form_name in all_form_names}
        for form in all_form_names:
            form_data = db_func.retrieve_form_details(
                form_name=form, immigrant_email=immigrant_email
            )
            form_details[form] = form_data

        return form_details
