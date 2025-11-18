from typing import Union, Literal


class DocumentsGateway:
    def crosscheck_existing(
        self, destination_path: str, filename: str
    ) -> tuple[str, str]:
        # TODO: Implement actual check
        modified_s3_path = f"{destination_path}/{filename}"
        modified_filename = filename
        return modified_s3_path, modified_filename

    def download_file(self, file_url: str) -> dict[str, Union[str, bytes]]:
        # TODO: Connect with s3 service
        pass

    def retrieve_all_immigrant_files(
        self, immigrant_username: str
    ) -> dict[str, list[str]]:
        # immigrant_files: dict[str, list[str]] = {}
        # file_subfolders = ["ai_chat_files", "forms", "personal_files", "filled_forms"]
        # for subfolder in file_subfolders:
        #     immigrant_files[subfolder] = []
        #     response = self.s3_client.list_objects_v2(
        #         Bucket=self.bucket_name,
        #         Prefix=f"immigrants/{immigrant_username.lower()}/{subfolder}/",
        #     )
        #     if "Contents" in response:
        #         for obj in response["Contents"]:
        #             file_key: str = obj["Key"]
        #             filename = file_key.split("/")[-1]
        #             if (
        #                 filename
        #                 and "blob" not in filename
        #                 and not self._is_image(filename)
        #             ):
        #                 immigrant_files[subfolder].append(f"{self.base_url}/{file_key}")
        # return immigrant_files
        # TODO: Connect with docs service
        pass

    def retrieve_all_lawpersonnel_files(
        self,
        lawpersonnel_username: str,
        lawpersonnel_type: Literal[
            "lawyers", "nonlawyers", "paralegals", "lawstudents"
        ],
    ) -> dict[str, list[str]]:
        # lawpersonnel_files: dict[str, list[str]] = {}
        # file_subfolders = [
        #     "ai_chat_files",
        #     "personal_files",
        #     "profile_picture",
        #     "government_ids",
        # ]
        # if lawpersonnel_type == "lawyers":
        #     file_subfolders.extend(
        #         ["intakes", "professional_licenses", "address_proofs"]
        #     )
        # for subfolder in file_subfolders:
        #     lawpersonnel_files[subfolder] = []
        #     response = self.s3_client.list_objects_v2(
        #         Bucket=self.bucket_name,
        #         Prefix=f"{lawpersonnel_type}/{lawpersonnel_username.lower()}/{subfolder}/",
        #     )
        #     if "Contents" in response:
        #         for obj in response["Contents"]:
        #             file_key: str = obj["Key"]
        #             filename = file_key.split("/")[-1]
        #             if (
        #                 filename
        #                 and "blob" not in filename
        #                 and not self._is_image(filename)
        #             ):
        #                 lawpersonnel_files[subfolder].append(
        #                     f"{self.base_url}/{file_key}"
        #                 )
        # return lawpersonnel_files
        # TODO: Connect with docs service
        pass
