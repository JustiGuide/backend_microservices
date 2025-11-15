class DocumentsGateway:
    def crosscheck_existing(
        self, destination_path: str, filename: str
    ) -> tuple[str, str]:
        # TODO: Implement actual check
        modified_s3_path = f"{destination_path}/{filename}"
        modified_filename = filename
        return modified_s3_path, modified_filename

    def upload_file(self, filepath: str, file_dir: str) -> str:
        # TODO: Implement actual upload
        return f"s3://bucket/{file_dir}/{filepath.split('/')[-1]}"

    def delete_file(self, file_url: str) -> str:
        # TODO: Implement actual delete
        pass
    