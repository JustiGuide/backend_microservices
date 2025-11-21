from openai import OpenAI
import os

class VectorUpload:
    VECTOR_STORE_ID = os.getenv(
        "OPINIONS_VECTOR_STORE_ID"
    )
    
    def __init__(self, vector_store_id=VECTOR_STORE_ID, file_paths=[], section=None):
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.store_id = vector_store_id
        self.section = section or "opinions"
        self.file_paths = file_paths or self.pending_uploads()
        self.upload = self.rag_upload()
        self.client = OpenAI(api_key=self.OPENAI_API_KEY)

    def check_downloaded_files(self):
        with open(f"{self.section}/downloaded.txt", "r") as file:
            downloaded = file.readlines()
            return downloaded

    def check_uploaded_files(self):
        with open(f"{self.section}/uploaded.txt", "r") as file:
            uploaded = file.readlines()
            return uploaded

    def pending_uploads(self):
        downloaded, uploaded = (
            [file.strip() for file in self.check_downloaded_files()],
            [file.strip() for file in self.check_uploaded_files()],
        )
        pending = [file for file in set(downloaded) if file not in set(uploaded)]
        return pending
    
    def rag_upload(self):
        try:
            file_paths = [
                f"{self.section}/downloads/{file}" for file in self.file_paths
            ]
            if not file_paths:
                return "No Pending Uploads."

            batch_size, uploaded = 10, []

            for i in range(0, len(file_paths), batch_size):
                current_batch = file_paths[i : i + batch_size]
                streams = [open(path, "rb") for path in current_batch]
                upload_batch = self.client.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=self.store_id, files=streams
                )
                [stream.close() for stream in streams]
                print(upload_batch.status)
                print(upload_batch.file_counts)
                print(f"Batch {i} to {i + batch_size} Upload Complete.")

                uploaded.extend(current_batch)

            print("All Uploads Complete.")

            with open(f"{self.section}/uploaded.txt", "a") as file:
                file.writelines(
                    f"{os.path.basename(uploaded_file)}\n" for uploaded_file in uploaded
                )

            return "All Uploads Complete, Check Vector Store."

        except Exception as exp:
            print(f"Exception Occurred While Uploading File: {exp}.")
