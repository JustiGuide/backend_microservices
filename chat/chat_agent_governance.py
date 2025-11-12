import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

headers = {"Authorization": f"Bearer {os.getenv('OWNLAYER_API_KEY')}"}

async def stream_inferences(user_input, ai_response, ai_assistant):
    url = "https://app.ownlayer.com/api/v1/inferences/"
    inference = {"input": user_input, "output": ai_response, "tags": [ai_assistant]}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=inference)
            response.raise_for_status()
            data = response.json()
            return data

        except httpx.HTTPError as error:
            return {"error": error}

        except Exception as error:
            return {"error": error}

class Governance:
    @staticmethod
    def ai_chat_information(user_input, ai_response, ai_assistant=None):
        assistants = {
            "relo": "ReLo",
            "dolores": "Dolores",
            "form": "Form",
            "help": "Helper",
            "lawyer": "Lawyer",
            "n400": "N400",
        }

        event_loop = asyncio.get_event_loop()
        event_loop.create_task(
            stream_inferences(user_input, ai_response, assistants.get(ai_assistant, "Void"))
        )
