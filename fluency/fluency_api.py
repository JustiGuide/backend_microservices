import asyncio
from datetime import datetime, timezone
import json
import os
from fastapi import HTTPException, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import websockets
from database import Functions
from .fluency_agent import FluencyHelper
from encryptor import Encrypt
from dotenv import load_dotenv
from response_schemas import CALL_SESSIONS, CallSession, FluencyAnalysisResponse, FluencyResponse, PracticeQuestionRequest, PracticeQuestionResponse

load_dotenv()

db_func = Functions()
fluency = FluencyHelper()

app = APIRouter()


@app.post("/fluency/immigrant/start-fluency-session/{immigrant_username}")
async def start_fluency_session(immigrant_username: str):
    immigrant = db_func.get_immigrant(immigrant_username)

    profile = db_func.retrieve_fluency_profile(immigrant_email=immigrant.email)
    session_response = await fluency.create_realtime_session()
    if session_response.success:
        raise HTTPException(status_code=500, detail=session_response.message)

    rt_id = session_response.session_data.get("session_id")
    rt_ws_url = session_response.session_data.get("ws_url")

    call_id = Encrypt.generate_uuid()
    CALL_SESSIONS[call_id] = CallSession(profile.uuid, rt_id, rt_ws_url)
    greet = (
        "Hello! I'm here to help you practise your spoken English fluency. "
        "I'll ask you questions similar to IELTS or TOEFL. "
        "To finish, say stop, goodbye, or click Hang Up. Are you ready?"
    )
    audio_b64 = await fluency.tts_wav(greet)

    return JSONResponse(
        {
            "call_id": call_id,
            "greeting_text": greet,
            "greeting_audio": audio_b64,
            "ws_url": rt_ws_url,
            "session_id": rt_id,
        }
    )


@app.websocket("/ws/fluency/immigrant/{call_id}")
async def fluency_ws(ws: WebSocket, call_id: str):
    """WebSocket bridge to OpenAI Realtime (from Legacy, Refactored)."""
    if call_id not in CALL_SESSIONS:
        await ws.close(code=4404)
        return

    sess = CALL_SESSIONS[call_id]
    await ws.accept()

    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
        "OpenAI-Beta": "realtime=v1",
    }

    try:
        async with websockets.connect(
            sess.rt_ws_url,
            extra_headers=headers,
            max_size=16 * 1024_1024,
            ping_interval=20,
            ping_timeout=20,
        ) as oa:

            await fluency._send_session_update(oa)

            async def receive_from_client():
                try:
                    async for msg in ws.iter_json():
                        if msg.get("audio"):
                            await oa.send(
                                json.dumps(
                                    {
                                        "type": "input_audio_buffer.append",
                                        "audio": msg["audio"],
                                    }
                                )
                            )
                        elif msg.get("hangup"):
                            await oa.close()
                            break
                except WebSocketDisconnect:
                    await oa.close()
                finally:
                    if oa.open:
                        await oa.close()

            async def receive_from_openai():
                async for raw in oa:
                    ev: dict = json.loads(raw)
                    t = ev.get("type")

                    if t == "response.output_item.done":
                        q = (
                            ev["item"]["content"][0]["transcript"]
                            if len(ev["item"]["content"]) > 0
                            else None
                        )
                        if q:
                            sess.history.append((q, ""))
                            await ws.send_json({"question": q})

                    elif t == "conversation.item.input_audio_transcription.completed":
                        answer: str = ev.get("transcript", "").strip()
                        q = ""
                        if answer:
                            cleaned_answer = "".join(
                                c for c in answer.lower() if c.isalnum() or c.isspace()
                            )
                            if cleaned_answer in {
                                "stop",
                                "quit",
                                "end",
                                "bye",
                                "goodbye",
                                "finish",
                                "i want to stop",
                            }:
                                answer = "stop_call"
                            else:
                                if sess.history:
                                    q, _ = sess.history.pop()
                                sess.history.append((q, answer))
                                sess.temp_blocks.append(
                                    {
                                        "timestamp": datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                        "question": q,
                                        "response": answer,
                                    }
                                )
                            await ws.send_json({"transcript": answer})

                    elif t == "response.audio.delta" and ev.get("delta"):
                        await ws.send_json({"audio_delta": ev["delta"]})
                    elif t == "response.audio.done":
                        await ws.send_json({"audio_done": True})
                    elif t == "error":
                        await ws.send_json({"error": ev.get("message")})

            await asyncio.gather(receive_from_client(), receive_from_openai())

    except Exception as e:
        print(f"Fluency WebSocket bridge error: {e}", exc_info=True)
    finally:
        if ws.client_state != "DISCONNECTED":
            await ws.close()


@app.post(
    "/fluency/immigrant/end-fluency-session/{call_id}",
    response_model=FluencyAnalysisResponse,
)
async def end_fluency_session(
    call_id: str
):
    if call_id not in CALL_SESSIONS:
        raise HTTPException(404, "Unknown call_id")

    sess = CALL_SESSIONS.pop(call_id)
    try:
        profile = db_func.retrieve_fluency_profile(profile_uuid=sess.profile_uuid)

        full_text = " ".join(f"AI: {q} User: {a}" for q, a in sess.history if a)
        if not full_text:
            return FluencyAnalysisResponse(
                success=False, message="No speech was detected during the session."
            )

        analysis_response = fluency.analyze(
            immigrant_email=profile.immigrant_email,
            transcript=full_text,
            interaction_record={
                "interaction_start": sess.start_at.isoformat(),
                "interaction_data": sess.temp_blocks,
            },
            interaction_type="realtime_fluency_session",
        )

        return analysis_response

    except Exception as e:
        return FluencyAnalysisResponse(
            success=False,
            message=f"An error occurred while finalizing the session: {e}",
        )


@app.post(
    "/fluency/immigrant/questions/generate", response_model=PracticeQuestionResponse
)
async def generate_practice_questions(request: PracticeQuestionRequest):
    """
    Generate personalized practice questions based on user's fluency level.
    """
    try:
        result_dict = await fluency.generate_practice_questions(
            username=request.username,
            difficulty_level=request.difficulty_level
        )

        return PracticeQuestionResponse(
            success=result_dict["success"],
            message="Practice questions generated successfully." if result_dict["success"] else result_dict.get("error", "Failed to generate questions"),
            questions=result_dict.get("questions", []),
            difficulty_level=request.difficulty_level,
            personalized_for=request.username,
            areas_targeted=result_dict.get("areas_targeted", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fluency/immigrant/profile/{username}", response_model=FluencyResponse)
async def get_fluency_profile(username: str):
    try:
        immigrant = db_func.get_immigrant(username)
        response = fluency.get_fluency_profile(immigrant_email=immigrant.email)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
