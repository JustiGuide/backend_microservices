"""
connect_lawyer
disconnect_lawyer
check_ifPending
decline_invite
saveLawyer
get_connLawyers
check_connLawyers
getLawyers
removeLawyers
new_sent_message
get_all_sent_messages
get_sent_message
change_sent_message_status
get_user_sent_messages
get_lawyer_sent_messages
DisconnectLawyer
invite_client
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

