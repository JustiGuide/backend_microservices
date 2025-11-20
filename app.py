from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import uvicorn
from autofill.autofill_api import app as autofill_api
from chat.chat_api import app as chat_api
from compiler.compiler_api import app as compiler_api
from fluency.fluency_api import app as fluency_api
from form_generator.form_generator_api import app as form_generator_api
from quiz_analyzer.analyzer_api import app as analyzer_api
from recommendation.recommendation_api import app as recommender_api
from signature_locator.locator_api import app as sign_locator_api
from task_generator.taskgen_api import app as task_generator_api
from twilio_handler.twilio_api import app as twilio_handler_api
from database import Functions

db_func=Functions()

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LawPersonnelRemoval(BaseModel):
    lawpersonnel_email: EmailStr
    immigrant_email: EmailStr

@app.post("/recommender/immigrant/remove-lawpersonnel")
async def remove_lawpersonnel_recommendation(payload: LawPersonnelRemoval):
    db_func.remove_lawyer_from_recommendations(
        payload.immigrant_email, payload.lawpersonnel_email
    )

app.include_router(autofill_api)
app.include_router(chat_api)
app.include_router(compiler_api)
app.include_router(fluency_api)
app.include_router(form_generator_api)
app.include_router(analyzer_api)
app.include_router(recommender_api)
app.include_router(sign_locator_api)
app.include_router(task_generator_api)
app.include_router(twilio_handler_api)

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8001
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=True
    )
