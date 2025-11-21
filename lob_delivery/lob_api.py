from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from .lob_module import LobMailing

app = APIRouter()

class CreateAddressInput(BaseModel):
    type: str = Literal["user_form_address", "uscis_mailing_address"]
    name: str
    email: str
    address_line1: str
    address_city: str
    address_state: str
    address_zip: str
    address_country: str = "US"
    company: str = None
    phone: str = None
    description: str = None
    metadata: dict[str, Any] = None


class AddressIdInput(BaseModel):
    address_id: str


class CreateLetterInput(BaseModel):
    to_address_id: str
    from_address_id: str
    file_url: str
    use_type: str = "operational"
    color: bool = True

class UsernameFormInput(BaseModel):
    username: str
    form_name: str = "N400"
    file_url: str = None

@app.post("/lob/create/address")
async def lob_create_address(
    payload: CreateAddressInput
):
    lob_mailing = LobMailing()
    return lob_mailing.create_address(payload)


@app.post("/lob/create/user-address")
async def lob_create_user_address(
    payload: UsernameFormInput
):
    lob_mailing = LobMailing()
    return lob_mailing.create_user_address(payload)


@app.get("/lob/list/addresses")
async def lob_list_addresses():
    lob_mailing = LobMailing()
    return lob_mailing.list_addresses()


@app.post("/lob/check/address")
async def lob_check_address(payload: AddressIdInput):
    lob_mailing = LobMailing()
    return lob_mailing.check_address(payload)


@app.post("/lob/check/user-address")
async def lob_check_user_address(
    payload: UsernameFormInput
):
    lob_mailing = LobMailing()
    return lob_mailing.check_user_address(payload)


@app.delete("/lob/delete/address")
async def lob_delete_address(payload: AddressIdInput):
    lob_mailing = LobMailing()
    return lob_mailing.delete_address(payload)


@app.post("/lob/send-letter")
async def lob_send_letter(payload: UsernameFormInput):
    lob_mailing = LobMailing()
    return lob_mailing.send_letter_prep(payload)


@app.post("/lob/webhooks")
async def lob_webhook(
    request: Request,
    lob_signature: str = Header(..., alias="Lob-Signature"),
    lob_timestamp: str = Header(..., alias="Lob-Signature-Timestamp"),
):
    raw_body = await request.body()
    lob_mailing = LobMailing()
    if not lob_mailing.verify_signature(raw_body, lob_signature, lob_timestamp):
        raise HTTPException(status_code=401, detail="Invalid Lob signature")
    return await lob_mailing.handle_webhook(request, lob_signature, lob_timestamp)


@app.post("/lob/webhooks-echo")
async def lob_webhooks_echo(request: Request):
    body = await request.body()
    headers = {key: value for key, value in request.headers.items()}
    print("\n--- [Lob Webhook ECHO] ---")
    print("Lob-Signature Header:", headers.get("lob-signature"))
    print("Content-Type:", headers.get("content-type"))
    print("All Headers:", headers)
    print("Raw Body (bytes):", list(body))
    print("Raw Body (text):", body.decode("utf-8", errors="replace"))
    print("--- [End Echo] ---\n")
    return {"status": "echoed"}
