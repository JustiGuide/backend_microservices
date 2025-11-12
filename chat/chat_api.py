import io
import os
from typing import Literal
from fastapi import Depends, File, Form, UploadFile, APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from authorization import (
    AudioFile,
    Authorizer,
    FormNameValidator,
    ImmigrantAIValidator,
    ImmigrantAgentValidator,
    ImmigrantChatLimitValidator,
    LawPersonnelAgentValidator,
    LawpersonnelAIValidator,
    TimestampValidator,
)
from database import Functions
from helpers import Helpers
from documents_gateway import DocumentsGateway
from .chat_agent import Chat
from rag_gateway import RAGGateway
import time
from pathlib import Path


class StartMessages(BaseModel):
    user: str
    assistant: str


class ChatAgentFeedback(BaseModel):
    username: str
    message_id: str
    feedback_content: str = None
    feedback_vote: str = Literal["upvote", "downvote", None]


class UsernameInput(BaseModel):
    username: str


class ImmigrantChatRetrieval(BaseModel):
    immigrant_email: ImmigrantAIValidator


class LawpersonnelChatRetrieval(BaseModel):
    lawpersonnel_email: LawpersonnelAIValidator


class LawpersonnelMessage(BaseModel):
    lawpersonnel_username: str
    message_id: str = Depends(Authorizer.lawpersonnel_message_validator)


db_func = Functions()
docs = DocumentsGateway()
chat = Chat()
rag_app = RAGGateway(config_name="balanced")

app = APIRouter()


@app.get("/ai-chat/immigrant/start-messages")
async def start_immigrant_messages(payload: StartMessages):
    responses = {
        "relo": "Hello! I'm Relo, your personal relocation assistant. I'm here to help you find the perfect place to move based on your unique needs and preferences. To get started, which language would you feel most comfortable communicating in?",
        "dolores": "I’m Dolores your immigration assistant. I’m here to help you with your immigration journey, and document preparation.",
        "form": "I’m Dolores your form assistant. I’m here to help you understand and translate your USCIS form to help you complete it before having a lawyer review it.",
        "help": "I’m Dolores your form assistant. I’m here to help you understand and translate your USCIS form to help you complete it before having a lawyer review it.",
        "n400": 'Welcome to the N-400 Naturalization Assistant! I can help you complete your Application for Naturalization form and answer questions about the process. Need to prepare for your citizenship interview? Use the "Start Quiz" button to test your knowledge with practice questions from the official USCIS test. How can I help you today?',
    }
    agent_response = responses[payload.assistant.lower()]
    response_timestamp = str(int(time.time() * 1000))
    immigrant = db_func.get_immigrant(payload.user)
    agent_message_id = db_func.store_immigrant_message(
        immigrant_email=immigrant.email,
        sender=payload.assistant,
        message=agent_response,
        references={},
        message_timestamp=response_timestamp,
    )
    agent_message_time = Helpers.format_date(
        db_func.get_timestamp_from_id(response_timestamp)
    )
    response = {
        "agent_response": agent_response,
        "response_timestamp": response_timestamp,
        "references": {},
        "agent_message_id": agent_message_id,
        "agent_message_time": agent_message_time,
    }

    return response


@app.get("/ai-chat/lawpersonnel/start-messages")
async def start_lawpersonnel_messages(payload: StartMessages):
    responses = {
        "form": "Hello, I'm here to assist you with your immigration law research and case review needs.",
        "lawyer": "Hello, I'm here to assist you with your immigration law research and case review needs.",
        "help": "Hello, I'm here to assist you with your immigration law research and case review needs.",
    }
    agent_response = responses[payload.assistant.lower()]
    response_timestamp = str(int(time.time() * 1000))
    lawpersonnel = db_func.get_lawpersonnel(payload.user)
    agent_message_id = db_func.store_lawpersonnel_message(
        lawyer_email=lawpersonnel.email,
        sender=payload.assistant,
        message=agent_response,
        references={},
        message_timestamp=response_timestamp,
    )
    agent_message_time = Helpers.format_date(
        db_func.get_timestamp_from_id(response_timestamp)
    )
    response = {
        "agent_response": agent_response,
        "response_timestamp": response_timestamp,
        "references": {},
        "agent_message_id": agent_message_id,
        "agent_message_time": agent_message_time,
    }

    return response


@app.post("/ai-chat/immigrant/generate-response")
async def immigrant_generate_response(
    immigrant_username: ImmigrantChatLimitValidator = Form(...),
    chat_prompt: str = Form(...),
    agent_selection: ImmigrantAgentValidator = Form(...),
    files: list[UploadFile] = File(...),
    message_timestamp: TimestampValidator = Form(...),
    form_name: FormNameValidator = Form(None),
    screenshot_base64: str = Form(None),
    page_url: str = Form(None),
):
    fileList = []
    destination_dir = f"immigrants/{immigrant_username.lower()}/chat_files"
    file_urls = []
    immigrant_obj = db_func.get_immigrant(immigrant_username)
    for file in files:
        if file.filename != "blob":
            tmp_filename = Helpers.get_legal_filename(file.filename)
            tmp_filePath = Path("./tmp/chat_files") / tmp_filename
            tmp_filePath.parent.mkdir(parents=True, exist_ok=True)
            s3_key, upd_file_name = docs.crosscheck_existing(destination_dir, tmp_filename)

            with open(tmp_filePath, "wb") as tmpFile:
                content = await file.read()
                tmpFile.write(content)
                if len(content) > 0:
                    fileList.append([tmp_filename, str(tmp_filePath)])

            file_url = docs.upload_file(str(tmp_filePath), s3_key)
            _ = Helpers.store_file(
                file=file,
                file_url=file_url,
                email_id=immigrant_obj.email,
                filename=upd_file_name,
            )
            db_func.add_immigrant_filedetails(
                immigrant_obj.email, file_url, "chat_files"
            )
            file_urls.append(file_url)

    immigrant_message_id = db_func.store_immigrant_message(
        immigrant_email=immigrant_obj.email,
        sender="user",
        message=chat_prompt,
        references={},
        message_timestamp=message_timestamp,
        documents=file_urls,
    )
    # agent_response, references = await chat.assistant(
    #     immigrant_username, chat_prompt, agent_selection, file_urls
    # )
    if agent_selection not in ["form", "help"]:
        agent_response, references = await chat.assistant(
            immigrant_username, chat_prompt, agent_selection, file_urls
        )
    elif agent_selection == "form":
        form_context = Helpers.get_form_context(form_name=form_name)
        agent_response, references = await chat.assistant(
            immigrant_username,
            chat_prompt,
            agent_selection,
            file_urls,
            form_context_json=form_context,
        )
    elif agent_selection == "help":
        site_context = Helpers.get_site_context(site="immigrant")
        agent_response, references = await chat.assistant(
            immigrant_username,
            chat_prompt,
            agent_selection,
            file_urls,
            site_context=site_context,
            screenshot_base64=screenshot_base64,
            page_url=page_url,
        )
    immigrant_message_time = Helpers.format_date(
        db_func.get_timestamp_from_id(message_timestamp)
    )
    response_timestamp = str(int(time.time() * 1000))
    agent_message_id = db_func.store_immigrant_message(
        immigrant_email=immigrant_obj.email,
        sender=agent_selection,
        message=agent_response,
        references=references,
        message_timestamp=response_timestamp,
    )
    db_func.reduce_immigrant_chat_limit(user_email=immigrant_obj.email)
    agent_message_time = Helpers.format_date(
        db_func.get_timestamp_from_id(response_timestamp)
    )
    response = {
        "agent_response": agent_response,
        "response_timestamp": response_timestamp,
        "references": references,
        "immigrant_message_id": immigrant_message_id,
        "agent_message_id": agent_message_id,
        "immigrant_message_time": immigrant_message_time,
        "agent_message_time": agent_message_time,
    }
    return response


@app.post("/ai-chat/lawpersonnel/generate-response")
async def lawpersonnel_generate_response(
    lawpersonnel_username: str = Form(...),
    chat_prompt: str = Form(...),
    agent_selection: LawPersonnelAgentValidator = Form(...),
    files: list[UploadFile] = File(...),
    message_timestamp: TimestampValidator = Form(...),
    form_name: FormNameValidator = Form(None),
    screenshot_base64: str = Form(None),
    page_url: str = Form(None),
):
    fileList = []
    lawpersonnel_obj = db_func.get_lawpersonnel(lawpersonnel_username)
    destination_dir = f"{lawpersonnel_obj.personnel_type}s/{lawpersonnel_obj.username.lower()}/chat_files"
    file_urls = []
    for file in files:
        if file.filename != "blob":
            tmp_filename = Helpers.get_legal_filename(file.filename)
            tmp_filePath = Path("./tmp/chat_files") / tmp_filename
            tmp_filePath.parent.mkdir(parents=True, exist_ok=True)
            s3_key, upd_file_name = docs.crosscheck_existing(destination_dir, tmp_filename)

            with open(tmp_filePath, "wb") as tmpFile:
                content = await file.read()
                tmpFile.write(content)
                if len(content) > 0:
                    fileList.append([tmp_filename, str(tmp_filePath)])

            file_url = docs.upload_file(str(tmp_filePath), s3_key)
            _ = Helpers.store_file(
                file=file,
                file_url=file_url,
                email_id=lawpersonnel_obj.email,
                filename=upd_file_name,
            )
            db_func.add_immigrant_filedetails(
                lawpersonnel_obj.email, file_url, "chat_files"
            )
            file_urls.append(file_url)

    lawpersonnel_message_id = db_func.store_lawpersonnel_message(
        lawpersonnel_email=lawpersonnel_obj.email,
        sender="user",
        message=chat_prompt,
        references={},
        message_timestamp=message_timestamp,
        documents=file_urls,
    )
    if agent_selection not in ["form", "help"]:
        agent_response, references = await chat.assistant(
            lawpersonnel_username, chat_prompt, agent_selection, file_urls
        )
    elif agent_selection == "form":
        form_context = Helpers.get_form_context(form_name=form_name)
        agent_response, references = await chat.assistant(
            lawpersonnel_username,
            chat_prompt,
            agent_selection,
            file_urls,
            form_context_json=form_context,
        )
    elif agent_selection == "help":
        site_context = Helpers.get_site_context(site="lawpersonnel")
        agent_response, references = await chat.assistant(
            lawpersonnel_username,
            chat_prompt,
            agent_selection,
            file_urls,
            site_context=site_context,
            screenshot_base64=screenshot_base64,
            page_url=page_url,
        )

    lawpersonnel_message_time = Helpers.format_date(
        db_func.get_timestamp_from_id(message_timestamp)
    )
    response_timestamp = str(int(time.time() * 1000))
    agent_message_id = db_func.store_lawpersonnel_message(
        lawpersonnel_email=lawpersonnel_obj.email,
        sender=agent_selection,
        message=agent_response,
        references=references,
        message_timestamp=response_timestamp,
    )
    agent_message_time = Helpers.format_date(
        db_func.get_timestamp_from_id(response_timestamp)
    )
    response = {
        "agent_response": agent_response,
        "response_timestamp": response_timestamp,
        "references": references,
        "lawpersonnel_message_id": lawpersonnel_message_id,
        "agent_message_id": agent_message_id,
        "lawpersonnel_message_time": lawpersonnel_message_time,
        "agent_message_time": agent_message_time,
    }
    return response


@app.post("/ai-chat/immigrant/post-feedback")
async def immigrant_post_feedback(payload: ChatAgentFeedback):
    immigrant_obj = db_func.get_immigrant(payload.username)
    rows_updated = False
    rows_updated = db_func.add_immigrant_chat_feedback(
        immigrant_email=immigrant_obj.email,
        message_id=payload.message_id,
        feedback=payload.feedback_content,
        vote=payload.feedback_vote,
    )
    return {"result": rows_updated}


@app.post("/ai-chat/immigrant/remove-feedback")
async def immigrant_post_feedback(payload: ChatAgentFeedback):
    immigrant_obj = db_func.get_immigrant(payload.username)
    rows_updated = False
    rows_updated = db_func.add_immigrant_chat_feedback(
        immigrant_email=immigrant_obj.email,
        message_id=payload.message_id,
        feedback=None,
        vote=None,
    )
    return {"result": rows_updated}


@app.post("/ai-chat/lawpersonnel-post-feedback")
async def lawpersonnel_post_feedback(payload: ChatAgentFeedback):
    lawpersonnel_obj = db_func.get_lawpersonnel(payload.username)
    rows_updated = False
    rows_updated = db_func.add_lawpersonnel_chat_feedback(
        lawpersonnel_email=lawpersonnel_obj.email,
        message_id=payload.message_id,
        feedback=payload.feedback_content,
        vote=payload.feedback_vote,
    )
    return {"result": rows_updated}


@app.post("/ai-chat/lawpersonnel/remove-feedback")
async def lawpersonnel_post_feedback(payload: ChatAgentFeedback):
    lawpersonnel_obj = db_func.get_lawpersonnel(payload.username)
    rows_updated = False
    rows_updated = db_func.add_lawpersonnel_chat_feedback(
        lawpersonnel_email=lawpersonnel_obj.email,
        message_id=payload.message_id,
        feedback=None,
        vote=None,
    )
    return {"result": rows_updated}


@app.post("/ai-chat/immigrant/delete-messages")
async def immigrant_delete_messages(payload: UsernameInput):
    immigrant_obj = db_func.get_immigrant(payload.username)
    db_func.delete_immigrant_ai_chat(immigrant_email=immigrant_obj.email)
    rag_app.delete_data_by_source(immigrant_obj.username, ["message_history"])


@app.post("/ai-chat/lawpersonnel/delete-messages")
async def lawpersonnel_delete_messages(payload: UsernameInput):
    lawpersonnel_obj = db_func.get_lawpersonnel(payload.username)
    db_func.delete_lawpersonnel_ai_chat(lawpersonnel_email=lawpersonnel_obj.email)
    rag_app.delete_data_by_source(lawpersonnel_obj.username, ["message_history"])


@app.post("/ai-chat/immigrant/retrieve-messages")
async def immigrant_retrieve_messages(payload: ImmigrantChatRetrieval):
    message_history = db_func.process_immigrant_messages(
        immigrant_email=payload.immigrant_email
    )
    sorted_messages = Helpers.sort_ai_messages(message_history)
    return JSONResponse(sorted_messages)


@app.post("/ai-chat/lawpersonnel/retrieve-messages")
async def lawpersonnel_retrieve_messages(payload: LawpersonnelChatRetrieval):
    message_history = db_func.process_lawpersonnel_messages(
        lawpersonnel_email=payload.lawpersonnel_email
    )
    sorted_messages = Helpers.sort_ai_messages(message_history)
    return JSONResponse(sorted_messages)


@app.post("/ai-chat/lawpersonnel/retrieve_starred")
async def lawpersonnel_retrieve_starred(payload: LawpersonnelChatRetrieval):
    message_history = db_func.process_lawpersonnel_messages(
        lawpersonnel_email=payload.lawpersonnel_email, starred=True
    )
    sorted_messages = Helpers.sort_ai_messages(message_history)
    return JSONResponse(sorted_messages)


@app.post("/ai-chat/lawpersonnel/{star_value}-ai-message")
async def lawpersonnel_star_messsage(star_value: str, payload: LawpersonnelMessage):
    star_bool = star_value == "star"
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_username)
    db_func.update_lawpersonnel_message_favorite_bool(
        lawpersonnel_email=lawpersonnel.email,
        message_id=payload.message_id,
        favorite_bool=star_bool,
    )


@app.post("/ai-chat/lawpersonnel/delete-ai-message")
async def delete_lawpersonnel_ai_message(payload: LawpersonnelMessage):
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_username)
    db_func.delete_lawpersonnel_ai_message(
        lawpersonnel_email=lawpersonnel.email, message_id=payload.message_id
    )


@app.post("/ai-chat/get-transcript")
async def get_trascript(file: AudioFile):
    allowed_extensions = ["wav", "webm"]
    try:
        file_content = await file.read()
        original_extension = os.path.splitext(file.filename)[1].lstrip(".").lower()
        if original_extension not in allowed_extensions:
            audio_obj = await Helpers.get_wave_buffer(file_content)
        else:
            audio_obj = io.BytesIO(file_content)

        audio_obj.seek(0)
        audio_obj.name = (
            f"audio.{original_extension}"
            if original_extension in allowed_extensions
            else "audio.wav"
        )
        openai_client = chat.openai_client
        transcript = openai_client.audio.transcriptions.create(
            model="gpt-4o-transcribe", file=audio_obj
        ).text
        return {"content": transcript.capitalize()}
    except Exception as e:
        return {"error": str(e)}
