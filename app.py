from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from emailing_service.emailing_api import app as emailing_api
from twilio_service.twilio_api import app as twilio_api
from lawyer_chat.chat_api import app as lawyer_chat_api

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(emailing_api)
app.include_router(twilio_api)
app.include_router(lawyer_chat_api)


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8004
    uvicorn.run("app:app", host=host, port=port, reload=True)
