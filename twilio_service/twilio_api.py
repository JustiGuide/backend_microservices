import asyncio
import base64
import json
from typing import Literal
from fastapi import APIRouter, BackgroundTasks, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
import os
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import websockets

from authorization import PhoneNumber
from .twilio_module import TWILIO_BOT_PROMPT, send_session_update
from database import Functions

app = APIRouter()
db_func = Functions()

@app.post("/incoming-whatsapp")
async def twilio_whatsapp(request: Request, background_tasks: BackgroundTasks):
    data = await request.form()
    user_input = None
    if "Body" in data:
        twilio_client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_AUTH"))
        helper_number = os.getenv("TWILIO_NUM")
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        user_input = data["Body"]
        whatsapp_number = data["From"].split("whatsapp:")[-1]
        system_instructions = TWILIO_BOT_PROMPT
        system_instructions += """
        NOTE:
        Integration of Previous Summary:
        Sage will leverage a "Previous Summary" that combines key points from both user queries and Sage's prior responses. This summary provides context for ongoing interactions and ensures continuity across conversations. Sage must reference the provided "Previous Summary" to maintain context and avoid redundancy in responses.
        """
        user_context, ai_context = db_func.retrieve_twilio_context(
            user_number=whatsapp_number, contact_method="whatsapp"
        )
        summary_input = (
            f"Previous Summary: USER_CONTEXT: {user_context}, AI_CONTEXT: {ai_context}"
        )
        if user_input:
            user_message = f"{user_input} | {summary_input}"
            messages = [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_message},
            ]
            completion = client.chat.completions.create(
                model="gpt-5",
                messages=messages,
                reasoning_effort="medium",
            )
            answer = completion.choices[0].message.content
            try:
                message = twilio_client.messages.create(
                    from_=f"whatsapp:{helper_number}",
                    body=answer,
                    to=f"whatsapp:{whatsapp_number}",
                )
                background_tasks.add_task(
                    run_in_threadpool,
                    db_func.update_twilio_conversation,
                    whatsapp_number,
                    [
                        f"Previous Summary: {user_context}",
                        f"Previous Summary: {ai_context}",
                        user_input,
                        answer,
                    ],
                    "text",
                    user_input,
                    user_context,
                    answer,
                    ai_context,
                    whatsapp_number,
                    "whatsapp",
                )
            except Exception as e:
                print(f"Error sending message to {whatsapp_number}: {e}")


@app.post("/status-callback")
async def delivery_status_callback(request: Request):
    data = await request.form()
    print(f"Delivery Status Callback Data: {data}")
    return {"status": "received"}


@app.post("/incoming-message")
async def twilio_chat(request: Request, background_tasks: BackgroundTasks):
    data = await request.form()
    user_input = None
    if "Body" in data:
        user_input = data["Body"]
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        system_instructions = TWILIO_BOT_PROMPT
        system_instructions += """
        NOTE:
        Integration of Previous Summary:
        Sage will leverage a "Previous Summary" that combines key points from both user queries and Sage's prior responses. This summary provides context for ongoing interactions and ensures continuity across conversations. Sage must reference the provided "Previous Summary" to maintain context and avoid redundancy in responses.
        """
        user_context, ai_context = db_func.retrieve_twilio_context(
            user_number=data["From"], contact_method="text"
        )
        summary_input = (
            f"Previous Summary: USER_CONTEXT: {user_context}, AI_CONTEXT: {ai_context}"
        )
        if user_input:
            user_message = f"{user_input} | {summary_input}"
            messages = [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_message},
            ]
            completion = client.chat.completions.create(
                model="gpt-5",
                messages=messages,
                reasoning_effort="medium",
            )
            answer = completion.choices[0].message.content
            background_tasks.add_task(
                run_in_threadpool,
                db_func.update_twilio_conversation,
                data["From"],
                [
                    f"Previous Summary: {user_context}",
                    f"Previous Summary: {ai_context}",
                    user_input,
                    answer,
                ],
                "text",
                user_input,
                user_context,
                answer,
                ai_context,
                "text",
            )
            resp = MessagingResponse()
            resp.message(answer)
            return Response(content=str(resp), media_type="application/xml")


@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    user_number = request.query_params.get("From")
    """Handle incoming call and return TwiML response to connect to Media Stream."""
    response = VoiceResponse()
    response.play(
        url="https://doloreschatbucket.s3.us-east-2.amazonaws.com/ringtones/ringtone_singleRing.mp3",
        loop=1,
    )
    response.say(
        "Thank you for calling JustiGuide's AI helpline. Start speaking, right after this beep."
    )
    response.play(
        url="https://doloreschatbucket.s3.us-east-2.amazonaws.com/ringtones/start_beep.mp3",
        loop=1,
    )
    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f"wss://{host}/media-stream/{user_number}")
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")


@app.websocket("/media-stream/{user_num}")
async def handle_media_stream(
    websocket: WebSocket, user_num: str, background_tasks: BackgroundTasks
):
    """Handle WebSocket connections between Twilio and OpenAI."""
    LOG_EVENT_TYPES = ["response.content.done", "response.done"]
    await websocket.accept()
    call_transcript = []
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "OpenAI-Beta": "realtime=v1",
    }
    param = "extra_headers"
    if bool(int(os.getenv("IS_PROD"))):
        param = "additional_headers"
    connection_kwargs = {param: headers}

    async with websockets.connect(
        "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2025-06-03",
        **connection_kwargs,
    ) as openai_ws:
        await send_session_update(openai_ws)
        stream_sid = None

        async def receive_from_twilio():
            """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data["event"] == "media":
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data["media"]["payload"],
                        }
                        await openai_ws.send(json.dumps(audio_append))
                    elif data["event"] == "start":
                        stream_sid = data["start"]["streamSid"]
                    elif data["event"] == "stop":
                        background_tasks.add_task(
                            run_in_threadpool,
                            db_func.update_twilio_reason,
                            user_num,
                            call_transcript,
                            "call",
                        )

            except WebSocketDisconnect:
                try:
                    await openai_ws.close()
                except:
                    pass

        async def send_to_twilio():
            """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
            nonlocal stream_sid
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    if response["type"] in LOG_EVENT_TYPES:
                        try:
                            call_transcript.append(
                                response["response"]["output"][0]["content"][0][
                                    "transcript"
                                ]
                            )
                        except:
                            pass
                    if response["type"] == "response.audio.delta" and response.get(
                        "delta"
                    ):
                        try:
                            audio_payload = base64.b64encode(
                                base64.b64decode(response["delta"])
                            ).decode("utf-8")
                            audio_delta = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": audio_payload},
                            }
                            await websocket.send_json(audio_delta)
                        except Exception as e:
                            print(f"Error processing audio data: {e}")
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")

        await asyncio.gather(receive_from_twilio(), send_to_twilio())


class TwilioUpdate(BaseModel):
    user_number: PhoneNumber
    user_context: str
    ai_context: str
    contact_method: Literal["call", "text", "whatsapp"]


@app.post("/twilio/context/update")
async def update_twilio_context(payload: TwilioUpdate):
    db_func.update_twilio_context(user_number=payload.user_number, user_context=payload.user_context, ai_context=payload.ai_context, contact_method=payload.contact_method)


class TwilioInteractionInput(BaseModel):
    user_number: PhoneNumber
    contact_reason: str
    contact_method: Literal["call", "text", "whatsapp"]

@app.post("/twilio/interaction/add-new")
async def add_new_twilio_interaction(payload: TwilioInteractionInput):
    db_func.add_twilio_interaction(user_number=payload.user_number, contact_reason=payload.contact_reason, contact_method=payload.contact_method)

