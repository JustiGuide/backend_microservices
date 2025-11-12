import json
import os
from typing import Union
from fastapi import HTTPException, status
import requests


class DocumentsGateway:
    def crosscheck_existing(self, destination_path: str, filename: str) -> tuple[str, str]:
        # TODO: Implement actual check
        modified_s3_path = f"{destination_path}/{filename}"
        modified_filename = filename
        return modified_s3_path, modified_filename

    def is_exists(self, document_url: str) -> bool:
        try:
            response = requests.get(document_url)
            response.raise_for_status()
            return True
        except:
            return False

    def upload_file(self, filepath: str, file_dir: str) -> str:
        # TODO: Implement actual upload
        return f"s3://bucket/{file_dir}/{filepath.split('/')[-1]}"

    def get_formdetails_json(self, url: str) -> dict:
        form_details = {}
        try:
            response = requests.get(url)
            if response.status_code == 200:
                form_details = response.json()
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to retrieve form details at {url}"
                )
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to retrieve form details. Error occured: {e}",
            )
        return form_details

    def get_all_compiler_documents(self, immigrant_username: str, lawyer_map: dict[str, list[str]]) -> bytes:
        # TODO: Connect with s3 service
        pass

    def download_file(self, file_url: str) -> dict[str, Union[str, bytes]]:
        # TODO: Connect with s3 service
        pass

    def delete_dir(self, file_dir):
        # TODO: Connect with s3 service
        pass

    @staticmethod
    def get_n400_quiz() -> list[dict[str, Union[str, list[str]]]]:
        n400_questions = []
        n400_bank_filepath = "./data/n400_quizset.json"
        with open(n400_bank_filepath, "r") as file:
            n400_questions = json.load(file)

        return n400_questions