from fastapi import APIRouter, HTTPException
from database import Functions
import asyncio, random, time
from .uscis_module import USCIS

app = APIRouter()
db_func = Functions()
uscis = USCIS()

@app.get("/uscis/check")
async def check_uscis():
    return f"USCIS Routes Active."


@app.get("/uscis/access-token")
async def uscis_access_token():
    token = await uscis.get_access_token()
    return {"token": token, "headers": uscis.uscis_headers}


@app.get("/uscis/check-access-token")
async def check_access_token():
    token_time_left = uscis.token_expiry_time - time.time()
    minutes_left = round(token_time_left // uscis.seconds_value)
    seconds_left = round(token_time_left % uscis.seconds_value)

    return {
        "Access Token": (
            uscis.uscis_token if uscis.token_expiry_time else None
        ),
        "Token Status": (
            "Valid"
            if uscis.token_expiry_time
            and (token_time_left) > uscis.seconds_value
            else "Invalid"
        ),
        "Token Time Left": (
            f"{minutes_left} Minutes and {seconds_left} Seconds Left."
            if token_time_left > uscis.seconds_value
            else "Token Expired"
        ),
        "USCIS Headers": (
            uscis.uscis_headers if uscis.token_expiry_time else None
        ),
        "Token Change Condition": (
            f"TimeReceived&Expiring - CurrentTime < 1 Minute | {uscis.token_expiry_time - time.time() < uscis.seconds_value}"
            if uscis.token_expiry_time
            else None
        ),
        "Token Condition Compute": (
            f"TimeReceived&Expiring - CurrentTime = {uscis.token_expiry_time - time.time()}"
            if uscis.token_expiry_time
            else None
        ),
        "Current Environment": uscis.uscis_environment.capitalize(),
    }


@app.get("/uscis/get-case-status/{username}/{receipt_number}")
async def get_case_status(receipt_number: str, username: str):
    if not receipt_number:
        raise HTTPException(status_code=400, detail="Provide Receipt Number.")

    if (uscis.token_expiry_time - time.time()) > uscis.seconds_value:
        await uscis.get_access_token()

    user = db_func.get_immigrant(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    db_func.update_user_receipt_number(
        email_id=user.email, receipt_number=receipt_number
    )
    return await uscis.fetch_case_status(receipt_number)


@app.get("/uscis/too-many-requests")
async def too_many_requests():
    try:
        staging_receipt_number = uscis.single_receipt_number
        tasks = [
            uscis.fetch_case_status(staging_receipt_number) for _ in range(20)
        ]
        return await asyncio.gather(*tasks)
    except Exception as error:
        print(f"Too Many Requests Error: {error}")
        raise HTTPException(status_code=500, detail=f"Error: {error}")


@app.get("/uscis/request/run")
async def run_requests():
    try:
        random.shuffle(uscis.staging_receipt_numbers)
        for number in uscis.staging_receipt_numbers:
            status = await uscis.fetch_case_status(number)
            print(f"Case Status for {number}: {status}")
            await asyncio.sleep(2)

        return {
            "message": "Random Requests Completed.",
            "receipt_numbers": uscis.staging_receipt_numbers,
        }
    except Exception as error:
        print(f"Run Requests Error: {error}")
        raise HTTPException(status_code=500, detail=f"Error: {error}")
