from datetime import datetime, timezone
from fastapi import BackgroundTasks, APIRouter
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from authorization import (
    FormNameValidator
)
from database import Functions
from helpers import Helpers
from dotenv import load_dotenv
from background_utility import BackgroundUtilities

load_dotenv()

db_func = Functions()

app = APIRouter()

class ImmigrantAutofillData(BaseModel):
    immigrant_username: str
    form_name: FormNameValidator

@app.post("/autofill/immigrant/get-autofill-data")
async def get_immigrant_autofill_data(payload: ImmigrantAutofillData, background_tasks: BackgroundTasks):
    existing_autofill = db_func.retrieve_autofill_data(
        immigrant_username=payload.immigrant_username, form_name=payload.form_name
    )
    to_redo = False
    if not existing_autofill:
        to_redo = True
    
    if existing_autofill and (existing_autofill.created_at - datetime.now(timezone.utc)).days <= 7:
       to_redo = True 

    if to_redo:
        case_type = Helpers.get_casetype(payload.form_name)
        background_tasks.add_task(
            run_in_threadpool,
            BackgroundUtilities.start_autofill,
            immigrant_username=payload.immigrant_username,
            form_name=payload.form_name,
            case_type=case_type
        )
        return {
            "success": False,
            "message": "Autofill data is being generated. We'll email you once the data is ready",
            "fields": {}
        }
    return {
        "success": True,
        "message": "Autofill data retrieved successfully",
        "fields": existing_autofill
    }
