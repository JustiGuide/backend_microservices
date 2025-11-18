
from datetime import datetime, timezone, date
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from database import Functions
from authorization import Authorizer, SignID, UserSignID
from PIL import Image
from .sign_processing import SignGenerator

db_func = Functions()
app = APIRouter()
signer = SignGenerator()

class UploadInfo(BaseModel):
    user_agent: str
    client_ip: str
    x_forwarded_for: str

    def to_dict(self):
        return {
        "user_agent": self.user_agent,
        "client_ip": self.client_ip,
        "x_forwarded_for": self.x_forwarded_for,
    }

class HandshakePush(BaseModel):
    user_email: EmailStr
    upload_info: UploadInfo
    sign_data: bytes

@app.post("/signer/push-handshake")
async def push_handshake(payload: HandshakePush):
    sign_image = Image.open(payload.sign_data)
    todays_date = datetime.now(tz=timezone.utc).date()

    signer.push_sign(
        sign_object=sign_image,
        user_email=payload.user_email,
        upload_date=todays_date,
        upload_info=payload.upload_info.to_dict()
    )

class HandshakeRetrieval(BaseModel):
    user_email: EmailStr
    sign_id: UserSignID = None
    user_full_name: str = None


@app.post("/signer/retrieve-all")
async def retrieve_all_handshakes(payload: HandshakeRetrieval):
    all_signatures = signer.retrieve_signs(payload.user_email)
    return JSONResponse(all_signatures)

@app.post("/signer/retrieve-specific")
async def retrieve_specific_handshake(payload: HandshakeRetrieval):
    signature = signer.retrieve_signs(payload.user_email, sign_id=payload.sign_id, full_legal_name=payload.user_full_name)[0]
    return JSONResponse(signature)

class DeleteSign(BaseModel):
    sign_id: SignID


@app.post("/signer/delete-handshake")
async def delete_handshake(payload: DeleteSign):
    is_success = db_func.delete_sign(sign_id=payload.sign_id)
    return {"is_success": is_success}


class HandshakeUpdate(BaseModel):
    sign_id: SignID
    date: date

@app.post("/signer/update-handshake-date")
async def update_handshake_date(payload: HandshakeUpdate):
    db_func.update_sign_date(sign_id=payload.sign_id, today_date=payload.date)

@app.post("/signer/retrieve-handshake-image")
async def retrieve_handshake_image(payload: HandshakeRetrieval):
    signature = signer.retrieve_signs(
        payload.user_email,
        sign_id=payload.sign_id,
        full_legal_name=payload.user_full_name,
    )[0]
    return {"sign_base64": signature["sign_b64"]}

class CheckSignID(BaseModel):
    user_email: EmailStr = None
    sign_id: str

@app.post("/signer/check-user-id")
async def check_sign_id(payload: CheckSignID):
    sign_id = Authorizer.user_signid_validator(sign_id=payload.sign_id, user_email=payload.user_email)
    if sign_id:
        return {"is_sign": True}


@app.post("/signer/check-user-id")
async def check_sign_id(payload: CheckSignID):
    sign_id = Authorizer.sign_id_validator(sign_id=payload.sign_id)
    if sign_id:
        return {"is_sign": True}
