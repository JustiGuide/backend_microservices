"""
/intake/{form_id}
upload_intake_form
retrieve_intake_forms
delete_intake_form
sign_intake
"""
from datetime import datetime, timezone, date
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from database import Functions
from authorization import Authorizer
from PIL import Image

db_func = Functions()
app = APIRouter()
