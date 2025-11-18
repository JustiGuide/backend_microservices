from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from bucket_management.bucket_api import app as bucket_api
from form_management.formfiller_api import app as form_api
from signature_processing.signer_api import app as signer_api

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bucket_api)
app.include_router(form_api)
app.include_router(signer_api)


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8005
    uvicorn.run("app:app", host=host, port=port, reload=True)
