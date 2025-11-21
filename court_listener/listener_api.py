import random
from fastapi import APIRouter, HTTPException, Request
import asyncio
import httpx
from pydantic import BaseModel, HttpUrl
from .listener_module import CourtListener

app = APIRouter()
listener = CourtListener()

@app.get("/listener/check")
async def check_court_listener():
    return f"Court Listener Routes Active."


@app.get("/listener/crawl")
async def start_court_listener_crawl(request: Request):
    url = "https://www.courtlistener.com/api/rest/v4/opinions/"
    next_url = ""
    try:
        with open("opinions/next.txt", "r") as file:
            next_url = file.readline().strip()
            if next_url:
                url = next_url
                print(f"Next URL Available and Will Be Used: {url}")
            else:
                try:
                    data: dict = await request.json()
                    input_url = data.get("url", url)
                    url = input_url if input_url and len(input_url) >= 7 else url
                except Exception as exp:
                    print(
                        f"Url Not Provided & Next URL Not Available. Default URL Will Be Used: {url}. \nError:",
                        exp,
                    )
    except FileNotFoundError as err:
        print(f"File Not Found. Default URL Will Be Used: {url}. \nError:", err)

    crawl_consumption = await listener.crawl_court_listener(
        next_url if next_url else url
    )

    return crawl_consumption


class CheckCourtListenerUrl(BaseModel):
    url: HttpUrl = ""


@app.post("/listener/check-url")
async def check_cl_url(payload: CheckCourtListenerUrl):
    if len(payload.url) < 7:
        HTTPException(status_code=400, detail="Invalid URL")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                payload.url, headers=listener.court_listener_headers
            )

            response.raise_for_status()
            if response.status_code == 200:
                return response.text

            return {"Status Code": response.status_code}

        except httpx.HTTPError as error:
            return {"error": f"An HTTP Error Occurred: {error}"}

        except Exception as error:
            return {"error": f"An Error Occurred: {error}"}


@app.get("/listener/view-opinions")
async def view_opinions():
    return listener.get_saved_opinions()


@app.get("/listener/scrape-opinions")
async def scrape_opinions_content():
    opinions = listener.get_saved_opinions()
    if not opinions.get("opinions"):
        return opinions
    
    random_value = random.randint(1, 10)
    opinions_slice = random.sample(
        opinions.get("opinions"), random_value
    )

    for op in opinions_slice:
        opinion_content = await listener.scrape_consumed_opinions(op)
        await asyncio.sleep(random_value)
        print(opinion_content)

    return "Done, Check Files For Results."
