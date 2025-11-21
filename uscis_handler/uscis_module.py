# Import Dependencies
from fastapi import APIRouter, HTTPException
import tracemalloc, tenacity, asyncio, random, httpx, time, json, os
from database import Functions

router = APIRouter()
db_func = Functions()

tracemalloc.start()

class USCIS:
    uscis_environment = os.getenv("USCIS_ENVIRONMENT", "staging")
    uscis_client_id = (
        os.getenv("USCIS_STAGING_CONSUMER_KEY")
        if uscis_environment == "staging"
        else os.getenv("USCIS_CONSUMER_KEY")
    )
    uscis_client_secret = (
        os.getenv("USCIS_STAGING_CONSUMER_SECRET")
        if uscis_environment == "staging"
        else os.getenv("USCIS_CONSUMER_SECRET")
    )
    uscis_token = ""
    token_time_received = 0
    token_expiry_time = 0

    uscis_headers = {
        "Authorization": f"Bearer {uscis_token}",
        "demo_id": os.getenv("USCIS_DEMO_ID"),
    }
    conf_file_path = os.path.join("configs", "uscis_config.json")
    def __init__(self):
        try:
            with open(self.conf_file_path) as uscis_file:
                self.uscis_data: dict = json.load(uscis_file)
                self.staging_receipt_numbers = self.uscis_data.get(
                    "staging_receipt_numbers", []
                )
                self.single_receipt_number = (
                    random.choice(self.staging_receipt_numbers)
                    if self.staging_receipt_numbers
                    else None
                )
                self.seconds_value = self.uscis_data.get("seconds_value", 60)
        except FileNotFoundError:
            print(
                f"Configuration file not found at {self.conf_file_path}. Please check the path and try again."
            )
            self.staging_receipt_numbers = []
            self.single_receipt_number = None
            self.seconds_value = 60

    async def get_access_token(self):
        if (self.token_expiry_time - time.time()) > self.seconds_value:
            return self.uscis_token

        url = (
            "https://api-int.uscis.gov/oauth/accesstoken"
            if self.uscis_environment == "staging"
            else "https://api.uscis.gov/oauth/accesstoken"
        )
        uscis_data = {
            "grant_type": "client_credentials",
            "client_id": self.uscis_client_id,
            "client_secret": self.uscis_client_secret,
        }
        async with httpx.AsyncClient() as client:
            try:
                @tenacity.retry(
                    wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(3),
                )
                async def get_token_response():
                    return await client.post(url, data=uscis_data)

                response = await get_token_response()

                response.raise_for_status()

                token_object = response.json()
                if isinstance(token_object, dict):
                    self.uscis_token = token_object.get("access_token", "")
                    self.uscis_headers["Authorization"] = f"Bearer {self.uscis_token}"
                    self.token_time_received = time.time()
                    self.token_expiry_time = self.token_time_received + int(
                        token_object.get("expires_in", 0)
                    )

                return self.uscis_token

            except httpx.HTTPError as err:
                print(f"HTTP Error: Network Error. {err}")
                raise HTTPException(
                    status_code=500, detail=f"Network Error Contacting USCIS. {err}"
                )
            except Exception as error:
                print(f"Exception Error: {error}")

    async def fetch_case_status(self, receipt_number=None):
        if not receipt_number:
            raise HTTPException(
                status_code=400, detail="Bad request. Provide Receipt Number."
            )

        url = (
            f"https://api-int.uscis.gov/case-status/{receipt_number}"
            if self.uscis_environment == "staging"
            else f"https://api.uscis.gov/case-status/{receipt_number}"
        )

        async with httpx.AsyncClient() as client:
            try:
                @tenacity.retry(
                    wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(3),
                )
                async def get_status_response():
                    await self.get_access_token()
                    return await client.get(url, headers=self.uscis_headers)

                response = await get_status_response()

                if response.status_code == 200:
                    data = response.json()
                    return data

                elif response.status_code == 400:
                    raise HTTPException(
                        status_code=400,
                        detail="Bad request. Check your receipt number format and parameters.",
                    )

                elif response.status_code == 401:
                    raise HTTPException(
                        status_code=401,
                        detail="Unauthorized. Check your access token or credentials.",
                    )

                elif response.status_code == 403:
                    raise HTTPException(
                        status_code=403,
                        detail="Forbidden. You do not have permission to access this resource.",
                    )

                elif response.status_code == 404:
                    print("Case not found for receipt number.")
                    raise HTTPException(status_code=404, detail="Receipt number not found.")

                elif response.status_code == 422:
                    print("Uprocessible Entity.")
                    raise HTTPException(
                        status_code=422,
                        detail="Unprocessible Entity. Check your receipt number.",
                    )

                elif response.status_code == 429:
                    print("Rate Limit Exceeded!")
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Please try again later.",
                    )

                elif response.status_code in (500, 503):
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Server encountered an error at USCIS. Please try again later.",
                    )

                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Unexpected error: {response.status_code}",
                    )

            except httpx.HTTPError as error:
                print(f"HTTP Error: {error}")
                raise HTTPException(
                    status_code=500, detail=f"Error communicating with USCIS: {error}"
                )