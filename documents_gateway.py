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
        # TODO: Implement actual check
        modified_s3_path = f"{destination_path}/{filename}"
        modified_filename = filename
        return modified_s3_path, modified_filename

    def upload_file(
        self, file: DummyFile, bucket_directory: str, is_previewable: bool = True
    ):
        # bucket_directory = bucket_directory.replace(" ", "+")
        # file_path = f"./tmp/{file.name}.{file.ext}"
        # with open(file_path, "wb") as fp:
        #     fp.write(file.content)
        # if not is_previewable:
        #     self.s3_client.upload_file(
        #         Filename=file_path, Bucket=self.bucket_name, Key=bucket_directory
        #     )
        #     return f"{self.base_url}/{bucket_directory}"
        # with open(file_path, "rb") as stream:
        #     self.s3_client.upload_fileobj(
        #         FileObj=stream,
        #         Bucket=self.bucket_name,
        #         Key=bucket_directory,
        #         ExtraArgs={"ContentType": file.content_type, "ACL": "public-read"},
        #     )
        # return f"{self.base_url}/{bucket_directory}"
        # TODO: Connect with docs service
        pass


    def delete_user_file(self, file_url: str) -> None:
        # if file_url.startswith(self.base_url):
        #     file_url = file_url.removeprefix(f"{self.base_url}/")
        # elif file_url.startswith("https"):
        #     return

        # self.s3_client.delete_object(
        #     Bucket=self.bucket_name,
        #     Key=file_url
        # )
        # TODO: connect with docs service
        pass
