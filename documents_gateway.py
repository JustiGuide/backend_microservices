from typing import Literal, Union
from pydantic import BaseModel

class DummyFile(BaseModel):
    content: bytes
    size: int
    name: str
    ext: str
    content_type: str


class DocumentsGateway:
    def crosscheck_existing(
        self, destination_path: str, filename: str
    ) -> tuple[str, str]:
        # counter = 1
        # s3_key = f"{destination_path}/{filename}"
        # stem, ext = os.path.splitext(filename)
        # while self.get_object_head(s3_key):
        #     filename = f"{stem}_{counter}{ext}"
        #     counter += 1
        #     s3_key = f"{destination_path}/{filename}"
        # return s3_key, filename
        # TODO: Connect with documents management
        pass

    def upload_file(self, filepath: str, file_dir: str) -> str:
        # TODO: Implement actual upload
        pass

    def upload_new_profile_picture(
        self,
        file_data: bytes,
        user_type: Literal[
            "immigrants", "lawyers", "nonlawyers", "lawstudents", "paralegals"
        ],
        username: str,
    ) -> str:
        file = DummyFile(
            content=file_data,
            size=len(file_data),
            name="user",
            ext="png",
            content_type="image/png",
        )
        bucket_directory = f"{user_type}/{username}/profile_pic/user.png"
        return self.upload_file(file, bucket_directory, is_previewable=True)

    def create_directory(
        self,
        username: str,
        user_type: Literal[
            "immigrants", "lawyers", "nonlawyers", "lawstudents", "paralegals"
        ],
    ):
        # sub_folders = ["ai_chat_files", "personal_files", "profile_picture"]
        # if user_type == "immigrants":
        #     sub_folders.extend(["forms", "filled_forms"])
        # elif user_type == "lawyers":
        #     sub_folders.extend(
        #         ["intakes", "professional_licenses", "address_proofs", "government_ids"]
        #     )
        # else:
        #     sub_folders.append("government_ids")

        # for sub_folder in sub_folders:
        #     self.bucket.put_object(
        #         Key=f"{user_type.lower()}/{username.lower()}/{sub_folder}/",
        #         Body=b"",
        #         ACL="public-read",
        #     )
        # TODO: Connect with documents management
        pass

    def delete_user_directory(self, directory_url: str) -> None:
        # TODO: Connect with documents management
        pass

    def _is_image(self, filename: str) -> bool:
        return any(filename.lower().endswith(ext) for ext in self.image_extensions)

    def download_file(self, file_url: str) -> dict[str, Union[str, bytes]]:
        # parsed = url_parser.urlparse(file_url)
        # path = parsed.path
        # file_key = path.lstrip("/")
        # filename = file_key.split("/")[-1]
        # file_contents = {}

        # if filename and "blob" not in filename:
        #     try:
        #         file_obj = self.s3_client.get_object(
        #             Bucket=self.bucket_name, Key=file_key
        #         )
        #         file_content = file_obj["Body"].read()
        #         file_contents["filename"] = filename
        #         if filename.lower().endswith(".pdf"):
        #             if self._is_pdf_image(file_content):
        #                 file_contents["image_data"] = file_content
        #                 file_contents["content_type"] = "pdf_images"
        #             else:
        #                 text_content = self._extract_pdf_text(file_content)
        #                 if text_content is not None and text_content != "":
        #                     file_contents["content"] = text_content
        #                     file_contents["content_type"] = "text"

        #         elif self._is_image(filename):
        #             file_contents["image_data"] = file_content
        #             file_contents["content_type"] = "image"

        #         else:
        #             text_content = self._extract_text_content(filename, file_content)
        #             if text_content is not None and text_content != "":
        #                 file_contents["content"] = text_content
        #                 file_contents["content_type"] = "text"
        #     except Exception as e:
        #         print(f"Error downloading file {filename}: {e}")
        #         return {}

        # return file_contents
        # TODO: Connect with documents management
        pass

    def add_lawyer_verification_items(
        self,
        lawyer_username: str,
        professional_license_filename: str,
        professional_license_contents: bytes,
        address_proof_filename: str,
        address_proof_contents: bytes,
    ) -> tuple[str, str]:
        # TODO: Connect with documents management
        pass

    def add_government_id(
        self,
        lawpersonnel_username: str,
        lawpersonnel_type: str,
        government_id_contents: bytes,
        government_id_filename: str,
    ) -> str:
        # TODO: Connect with documents management
        pass
