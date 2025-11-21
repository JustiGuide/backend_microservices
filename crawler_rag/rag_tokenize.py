
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import requests
import openai
import os
load_dotenv()

class TokenVectorUpload:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    VECTOR_STORE_ID = os.getenv("OPINIONS_VECTOR_STORE_ID")
    VECTOR_STORE_URL = os.getenv("OPINIONS_VECTOR_STORE_URL")
    openai.api_key = OPENAI_API_KEY
    
    def __init__(self, file_path, metadata=None):
        self.file_path = file_path
        self.metadata = metadata or {
            "title": "JustiGuide Upload",
            "category": "Opinions",
        }
        self.upload_result = self.begin_upload()

    def begin_upload(self):
        text = self.extract_pdf_text()
        text_chunks = self.read_to_chunks(text)
        text_embeddings = self.generate_embeddings(text_chunks)
        upload = self.vector_store_upload(text_embeddings, self.metadata)
        print("Upload Complete.")

        return upload
    
    def extract_pdf_text(self):
        reader = PdfReader(self.file_path)
        text = ""

        try:
            for line in reader.pages:
                text += line.extract_text()
        except Exception as exp:
            print(f"Exception Occurred While Reading File: {exp}.")

        return text
    
    def read_to_chunks(self, text, chunk_size=500):
        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
        return chunks
    
    def generate_embeddings(self, chunks):
        embeddings = []
        try:
            for chunk in chunks:
                response = openai.embeddings.create(
                    input=chunk, model="text-embedding-ada-002"
                )
                embedding = response.data[0].embedding
                embeddings.append((chunk, embedding))

        except Exception as exp:
            print(f"Exception Occurred While Creating Embedding: {exp}.")

        return embeddings

    def vector_store_upload(self, embeddings, metadata=None):
        successful_chunk_uploads = 0
        try:
            for chunk, embedding in embeddings:
                payload = {
                    "embedding": embedding,
                    "metadata": metadata or {},
                    "text": chunk
                }

                response = requests.post(
                    f"{self.VECTOR_STORE_URL}/documents", json=payload
                )

                if response.status_code == 200:
                    print(f"Successfully Uploaded Chunk: {chunk[:50]}")
                    successful_chunk_uploads += 1
                else:
                    print(f"Failed To Upload Chunk - Error: {response.text}")
        except Exception as exp:
            print(f"Exception Occurred While Uploading Embedding: {exp}.")

        print(f"{successful_chunk_uploads} of {len(embeddings)} Successfully Uploaded.")