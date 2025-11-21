
import requests


class DocumentsGateway:
    base_url = ""
    # TODO: connect with docs service
    def upload_web_file(self, web_url: str, file_key: str) -> str:
        # resp = requests.get(web_url, stream=True)
        # self.s3_client.upload_fileobj(
        #     Fileobj=resp.raw,
        #     Bucket=self.bucket_name,
        #     Key=file_key,
        #     ExtraArgs={"ACL": "public-read"},
        # )
        # return f"{self.base_url}/{file_key}"
        # TODO: Connect with docs service
        pass


    def add_empty_first_page(self, pdf_url: str) -> bool:
        # TODO: Connect with docs service
        pass
