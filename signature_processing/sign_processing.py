import base64
from datetime import datetime, date, timezone
import io
from typing import Union
from pydantic import EmailStr
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import numpy as np
from database import Functions


db_func = Functions()


class SignGenerator:
    TEXT_PADDING = 10
    BRACKET_THICKNESS = 5
    BRACKET_AREA_PADDING = 5
    INITIAL_NAME_FONT_SIZE = 48
    INITIAL_DATE_FONT_SIZE = 32
    INITIAL_ID_FONT_SIZE = 20
    MAX_BRACKET_ARM_LEN_ABS = 125
    MIN_BRACKET_ARM_LEN_ABS = 50

    threshold = 115
    erode = 1
    dilate = 1
    morph_kernel = 3

    center_of_mass_k = 2.5
    trim_amt = 5
    bracket_color = (80, 128, 222, 255)

    STANDARD_SIGNATURE_SLOT_WIDTH = 225 * 2
    STANDARD_SIGNATURE_SLOT_HEIGHT = 150 * 2

    FINAL_IMAGE_WIDTH = 250 * 2
    FINAL_IMAGE_HEIGHT = 210 * 2

    FINAL_IMAGE_MARGIN_HORIZONTAL = 3
    FINAL_IMAGE_MARGIN_VERTICAL = 3

    def get_fitted_font(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        max_width: int,
        max_height: int,
        initial_size: int,
        font_path: str = "./fonts/Nunito-Medium.ttf",
        min_size=12,
    ) -> ImageFont.FreeTypeFont:
        font_size = initial_size
        font = ImageFont.truetype(font_path, font_size)
        while font_size > min_size:
            font = ImageFont.truetype(font_path, font_size)
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            if text_width <= max_width and text_height <= max_height:
                break

            if font_size == min_size:
                break
            font_size -= 1

        return font

    def get_trimmed_bbox(
        self, image_rgba: Image.Image, initial_bbox: tuple[int, int, int, int]
    ) -> Union[tuple[int, int, int, int], None]:
        if image_rgba.mode != "RGBA":
            image_rgba = image_rgba.convert("RGBA")

        if not initial_bbox:
            return None

        l, t, r, b = initial_bbox
        img_width, img_height = image_rgba.size
        l, t, r, b = max(0, l), max(0, t), min(img_width, r), min(img_height, b)

        if l >= r or t >= b:
            return None

        new_t = t
        for y in range(t, b):
            if (
                sum(1 for x in range(l, r) if image_rgba.getpixel((x, y))[3] > 0)
                >= self.trim_amt
            ):
                new_t = y
                break
        else:
            return None
        t = new_t

        new_b = b
        for y in range(b - 1, t - 1, -1):
            if (
                sum(1 for x in range(l, r) if image_rgba.getpixel((x, y))[3] > 0)
                >= self.trim_amt
            ):
                new_b = y + 1
                break
        else:
            return None
        b = new_b

        new_l = l
        for x in range(l, r):
            if (
                sum(1 for y in range(t, b) if image_rgba.getpixel((x, y))[3] > 0)
                >= self.trim_amt
            ):
                new_l = x
                break
        else:
            return None
        l = new_l

        new_r = r
        for x in range(r - 1, l - 1, -1):
            if (
                sum(1 for y in range(t, b) if image_rgba.getpixel((x, y))[3] > 0)
                >= self.trim_amt
            ):
                new_r = x + 1
                break
        else:
            return None
        r = new_r

        return (l, t, r, b) if l < r and t < b else None

    def process_sign(self, original_sign: Image.Image) -> Image.Image:
        sign_gray = original_sign.convert("L")
        binary_mask = sign_gray.point(lambda p: 0 if p < self.threshold else 255, "1")
        temp_morph = binary_mask.convert("L")
        if self.erode > 0:
            for _ in range(self.erode):
                temp_morph = temp_morph.filter(ImageFilter.MinFilter(self.morph_kernel))
        if self.dilate > 0:
            for _ in range(self.dilate):
                temp_morph = temp_morph.filter(ImageFilter.MaxFilter(self.morph_kernel))

        extracted_sign = Image.new("RGBA", sign_gray.size, (255, 255, 255, 0))
        extracted_pixels = [
            (0, 0, 0, 255) if temp_morph.getpixel((x, y)) == 0 else (255, 255, 255, 0)
            for y in range(temp_morph.height)
            for x in range(temp_morph.width)
        ]
        extracted_sign.putdata(extracted_pixels)

        inverted_morph = ImageOps.invert(temp_morph)
        sign_array = np.array(inverted_morph)
        total_mass = np.sum(sign_array)
        initial_bbox = None
        if total_mass > 0:
            y, x = np.indices(sign_array.shape)

            mean_x = np.sum(x * sign_array) / total_mass
            mean_y = np.sum(y * sign_array) / total_mass

            var_x = np.sum((x - mean_x) ** 2 * sign_array) / total_mass
            var_y = np.sum((y - mean_y) ** 2 * sign_array) / total_mass

            std_x = np.sqrt(var_x) if var_x > 0 else 0
            std_y = np.sqrt(var_y) if var_y > 0 else 0

            initial_bbox = (
                max(0, int(mean_x - self.center_of_mass_k * std_x)),
                max(0, int(mean_y - self.center_of_mass_k * std_y)),
                min(sign_array.shape[1], int(mean_x + self.center_of_mass_k * std_x)),
                min(sign_array.shape[0], int(mean_y + self.center_of_mass_k * std_y)),
            )

        if not initial_bbox:
            initial_bbox = extracted_sign.getbbox()
        trimmed_bbox = self.get_trimmed_bbox(extracted_sign, initial_bbox)
        final_bbox = trimmed_bbox if trimmed_bbox else initial_bbox
        if (
            final_bbox
            and final_bbox[2] - final_bbox[0] > 0
            and final_bbox[3] - final_bbox[1] > 0
        ):
            cropped_signature_content = extracted_sign.crop(final_bbox)

            original_width, original_height = cropped_signature_content.size
            if original_width > 0 or original_height > 0:
                aspect_ratio = float(original_width) / original_height

                scaled_content_width = self.STANDARD_SIGNATURE_SLOT_WIDTH
                scaled_content_height = (
                    int(scaled_content_width / aspect_ratio)
                    if aspect_ratio != 0
                    else self.STANDARD_SIGNATURE_SLOT_HEIGHT
                )

                if scaled_content_height > self.STANDARD_SIGNATURE_SLOT_HEIGHT:
                    scaled_content_height = self.STANDARD_SIGNATURE_SLOT_HEIGHT
                    scaled_content_width = int(scaled_content_height * aspect_ratio)

                scaled_content_width = max(1, scaled_content_width)
                scaled_content_height = max(1, scaled_content_height)

                resized_signature_content = cropped_signature_content.resize(
                    (scaled_content_width, scaled_content_height),
                    Image.Resampling.LANCZOS,
                )
                signature_slot_image = Image.new(
                    "RGBA",
                    (
                        self.STANDARD_SIGNATURE_SLOT_WIDTH,
                        self.STANDARD_SIGNATURE_SLOT_HEIGHT,
                    ),
                    (255, 255, 255, 0),
                )

                paste_x = (
                    self.STANDARD_SIGNATURE_SLOT_WIDTH - scaled_content_width
                ) // 2
                paste_y = (
                    self.STANDARD_SIGNATURE_SLOT_HEIGHT - scaled_content_height
                ) // 2

                signature_slot_image.paste(
                    resized_signature_content,
                    (paste_x, paste_y),
                    resized_signature_content,
                )
                return signature_slot_image
        return None

    def push_sign(
        self,
        sign_object: Image.Image,
        user_email: EmailStr,
        upload_date: date,
        upload_info: dict[str, str],
    ) -> None:
        sign_object = self.process_sign(sign_object)
        byte_buffer = io.BytesIO()
        sign_object.save(byte_buffer, format="PNG")
        sign_bytes = byte_buffer.getvalue()
        db_func.add_new_handshake(user_email=user_email, sign_bytes=sign_bytes, upload_date=upload_date, upload_info=upload_info)


    def retrieve_signs(
        self,
        user_email: EmailStr,
        sign_id: str = None,
        full_legal_name: str = None,
    ) -> list[dict[str, Union[str, None]]]:
        signs = []
        all_signs = db_func.retrieve_all_signs(user_email)
        today_date = datetime.now(tz=timezone.utc).date()
        user = db_func.get_immigrant(user_email) or db_func.get_lawpersonnel(user_email)
        if full_legal_name is None:
            full_legal_name = user.full_legal_name
        for sign in all_signs:
            if sign.to_show:
                sign_buffer = io.BytesIO(sign.handshake_data)
                sign_obj = Image.open(sign_buffer)
                if sign_id is not None:
                    unique_id = f"{user.username}-{today_date.year}{today_date.month:02d}{today_date.day:02d}-{sign.uuid}"
                    sign_obj = self.add_sign_info(
                        sign_obj, full_legal_name, today_date.isoformat(), unique_id
                    )
                byte_buffer = io.BytesIO()
                sign_obj.save(byte_buffer, format="PNG")
                sign_bytes = byte_buffer.getvalue()
                sign_b64 = base64.b64encode(sign_bytes).decode("utf-8")
                signs.append(
                    {
                        "sign_id": sign.uuid,
                        "sign_b64": sign_b64,
                        "last_used": (
                            sign.last_used.isoformat() if sign.last_used else None
                        ),
                        "upload_date": (
                            sign.upload_date.isoformat() if sign.upload_date else None
                        ),
                    }
                )
        signs = (
            [sign_val for sign_val in signs if sign_val["sign_id"] == sign_id]
            if sign_id
            else signs
        )
        if sign_id is not None:
            db_func.update_sign_date(sign_id, today_date)
        return signs

    def get_sign_Image(self, sign_b64: Union[str, None], in_bytes: bool = False) -> Image.Image:
        if sign_b64 is None:
            return None
        sign_bytes = base64.b64decode(sign_b64)
        if in_bytes:
            return sign_bytes
        sign_buffer = io.BytesIO(sign_bytes)
        sign_obj = Image.open(sign_buffer)
        return sign_obj

    def add_sign_info(
        self,
        signature_slot_image: Image.Image,
        name_str: str,
        date_str: str,
        unique_id_str: str,
    ) -> Image.Image:
        final_image = Image.new(
            "RGBA",
            (self.FINAL_IMAGE_WIDTH, self.FINAL_IMAGE_HEIGHT),
            (255, 255, 255, 0),
        )
        draw_final = ImageDraw.Draw(final_image)

        y_cursor = self.FINAL_IMAGE_MARGIN_VERTICAL
        sig_slot_x = (self.FINAL_IMAGE_WIDTH - self.STANDARD_SIGNATURE_SLOT_WIDTH) / 2.0
        sig_slot_y_top = y_cursor
        final_image.paste(
            signature_slot_image, (int(sig_slot_x), int(y_cursor)), signature_slot_image
        )
        y_cursor += self.STANDARD_SIGNATURE_SLOT_HEIGHT
        y_cursor += self.TEXT_PADDING

        max_text_width_for_fitting = self.FINAL_IMAGE_WIDTH - 2 * (
            self.FINAL_IMAGE_MARGIN_HORIZONTAL
            + self.BRACKET_AREA_PADDING
            + self.MIN_BRACKET_ARM_LEN_ABS
        )
        max_text_height_for_fitting = self.INITIAL_NAME_FONT_SIZE * 2

        name_font = self.get_fitted_font(
            draw_final,
            name_str,
            max_text_width_for_fitting,
            max_text_height_for_fitting,
            self.INITIAL_NAME_FONT_SIZE,
        )
        name_bbox = draw_final.textbbox((0, 0), name_str, font=name_font)
        name_w, name_h = name_bbox[2] - name_bbox[0], name_bbox[3] - name_bbox[1]
        name_x_start = (self.FINAL_IMAGE_WIDTH - name_w) / 2.0
        draw_final.text(
            (name_x_start, y_cursor - name_bbox[1]),
            name_str,
            font=name_font,
            fill=(0, 0, 0, 255),
        )
        name_actual_top = y_cursor - name_bbox[1]
        name_actual_bottom = name_actual_top + name_h
        y_cursor = name_actual_bottom + self.TEXT_PADDING

        date_font = self.get_fitted_font(
            draw_final,
            date_str,
            max_text_width_for_fitting,
            max_text_height_for_fitting,
            self.INITIAL_DATE_FONT_SIZE,
        )
        date_bbox = draw_final.textbbox((0, 0), date_str, font=date_font)
        date_w, date_h = date_bbox[2] - date_bbox[0], date_bbox[3] - date_bbox[1]
        date_x_start = (self.FINAL_IMAGE_WIDTH - date_w) / 2.0
        draw_final.text(
            (date_x_start, y_cursor - date_bbox[1]),
            date_str,
            font=date_font,
            fill=(0, 0, 0, 255),
        )
        date_actual_top = y_cursor - date_bbox[1]
        date_actual_bottom = date_actual_top + date_h

        content_y1_tight = sig_slot_y_top
        content_y2_tight = date_actual_bottom

        sig_x1_tight = sig_slot_x
        sig_x2_tight = sig_slot_x + self.STANDARD_SIGNATURE_SLOT_WIDTH

        name_x1_tight = name_x_start
        name_x2_tight = name_x_start + name_w

        date_x1_tight = date_x_start
        date_x2_tight = date_x_start + date_w

        overall_content_x1_tight = min(sig_x1_tight, name_x1_tight, date_x1_tight)
        overall_content_x2_tight = max(sig_x2_tight, name_x2_tight, date_x2_tight)

        bp_x1 = overall_content_x1_tight - self.BRACKET_AREA_PADDING
        bp_y1 = content_y1_tight - self.BRACKET_AREA_PADDING
        bp_x2 = overall_content_x2_tight + self.BRACKET_AREA_PADDING
        bp_y2 = content_y2_tight + self.BRACKET_AREA_PADDING

        id_h_approx = self.INITIAL_ID_FONT_SIZE * 1.5
        bp_x1 = max(bp_x1, self.FINAL_IMAGE_MARGIN_HORIZONTAL)
        bp_y1 = max(bp_y1, self.FINAL_IMAGE_MARGIN_VERTICAL)
        bp_x2 = min(bp_x2, self.FINAL_IMAGE_WIDTH - self.FINAL_IMAGE_MARGIN_HORIZONTAL)
        bp_y2 = min(
            bp_y2,
            self.FINAL_IMAGE_HEIGHT
            - self.FINAL_IMAGE_MARGIN_VERTICAL
            - id_h_approx
            - self.TEXT_PADDING,
        )

        if bp_x1 < bp_x2 or bp_y1 < bp_y2:
            bracket_arm_len = float(date_w)
            max_arm_from_width = (bp_x2 - bp_x1) / 2.5
            max_arm_from_height = (bp_y2 - bp_y1) / 2.5

            bracket_arm_len = min(
                bracket_arm_len,
                max_arm_from_width,
                max_arm_from_height,
                self.MAX_BRACKET_ARM_LEN_ABS,
            )
            bracket_arm_len = max(bracket_arm_len, self.MIN_BRACKET_ARM_LEN_ABS)

            # Top-Left Bracket
            draw_final.line(
                [(bp_x1, bp_y1), (bp_x1, bp_y1 + bracket_arm_len)],
                fill=self.bracket_color,
                width=self.BRACKET_THICKNESS,
            )
            draw_final.line(
                [(bp_x1, bp_y1), (bp_x1 + bracket_arm_len, bp_y1)],
                fill=self.bracket_color,
                width=self.BRACKET_THICKNESS,
            )

            # Top-Right Bracket
            draw_final.line(
                [(bp_x2, bp_y1), (bp_x2, bp_y1 + bracket_arm_len)],
                fill=self.bracket_color,
                width=self.BRACKET_THICKNESS,
            )
            draw_final.line(
                [(bp_x2, bp_y1), (bp_x2 - bracket_arm_len, bp_y1)],
                fill=self.bracket_color,
                width=self.BRACKET_THICKNESS,
            )

            # Bottom-Left Bracket
            draw_final.line(
                [(bp_x1, bp_y2), (bp_x1, bp_y2 - bracket_arm_len)],
                fill=self.bracket_color,
                width=self.BRACKET_THICKNESS,
            )
            draw_final.line(
                [(bp_x1, bp_y2), (bp_x1 + bracket_arm_len, bp_y2)],
                fill=self.bracket_color,
                width=self.BRACKET_THICKNESS,
            )

            # Bottom-Right Bracket
            draw_final.line(
                [(bp_x2, bp_y2), (bp_x2, bp_y2 - bracket_arm_len)],
                fill=self.bracket_color,
                width=self.BRACKET_THICKNESS,
            )
            draw_final.line(
                [(bp_x2, bp_y2), (bp_x2 - bracket_arm_len, bp_y2)],
                fill=self.bracket_color,
                width=self.BRACKET_THICKNESS,
            )

        id_max_width = self.FINAL_IMAGE_WIDTH - 2 * self.FINAL_IMAGE_MARGIN_HORIZONTAL
        id_max_height = self.INITIAL_ID_FONT_SIZE * 2

        id_font_path = "./fonts/Nunito-MediumItalic.ttf"
        id_font = self.get_fitted_font(
            draw_final,
            unique_id_str,
            id_max_width,
            id_max_height,
            self.INITIAL_ID_FONT_SIZE,
            font_path=id_font_path,
        )

        id_bbox = draw_final.textbbox((0, 0), unique_id_str, font=id_font)
        id_w = id_bbox[2] - id_bbox[0]
        id_h = id_bbox[3] - id_bbox[1]

        id_x_start = self.FINAL_IMAGE_WIDTH - self.FINAL_IMAGE_MARGIN_HORIZONTAL - id_w
        id_actual_top = (
            self.FINAL_IMAGE_HEIGHT - self.FINAL_IMAGE_MARGIN_VERTICAL - id_h
        )

        draw_final.text(
            (id_x_start, id_actual_top - id_bbox[1]),
            unique_id_str,
            font=id_font,
            fill=(0, 0, 0, 255),
        )

        pixels = final_image.load()
        for i in range(final_image.width):
            for j in range(final_image.height):
                r, g, b, a = pixels[i, j]
                if a == 0:
                    pixels[i, j] = (255, 255, 255, 0)
                elif (r, g, b, a) == self.bracket_color:
                    pixels[i, j] = self.bracket_color
                else:
                    pixels[i, j] = (0, 0, 0, a)
        return final_image
