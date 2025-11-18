from typing import Literal
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import Functions
from .rag_app import RAGApplication

db_func = Functions()
app = APIRouter()

class RetrievalContextInput(BaseModel):
    rag_config: Literal["speed", "accuracy", "balanced", "large_scale", "development"] = "balanced"
    username: str
    query: str
    file_urls: list[str] = None
    top_k_files: int = 5
    top_k_general: int = 3

@app.post("/rag/retrieve/hybrid-context")
async def retrieve_hybrid_context(payload: RetrievalContextInput):
    rag_app = RAGApplication(rag_config=payload.rag_config)
    context = rag_app.retrieve_hybrid_context(username=payload.username, query=payload.query, file_urls=payload.file_urls, top_k_files=payload.top_k_files, top_k_general=payload.top_k_general)
    return {"context": context}

class DeleteSource(BaseModel):
    username: str
    sources: Literal["kyc_summary", "user_profile", "message_history", "uploaded_text", "uploaded_image", "uploaded_document"] = None

@app.post("/rag/delete-source")
async def delete_source(payload: DeleteSource):
    rag_app = RAGApplication()
    success = rag_app.delete_by_source(username=payload.username, sources=payload.sources)
    return {"is_success": success}

@app.get("/rag/retrieve-kyc-map")
async def retrieve_kyc_map():
    kyc_map = db_func.load_kyc_map()
    return JSONResponse(kyc_map)

class VectorSourceUpdate(BaseModel):
    rag_config: Literal["speed", "accuracy", "balanced", "large_scale", "development"] = "balanced"
    username: str

@app.post("/rag/setup-all-sources")
async def setup_all_source(payload: VectorSourceUpdate):
    rag_app = RAGApplication(rag_config=payload.rag_config)
    success = rag_app.setup_or_update_all_sources(username=payload.username)
    return {"is_success": success}


@app.post("/rag/delete-store")
async def delete_entire_store(payload: DeleteSource):
    rag_app = RAGApplication()
    success = rag_app.delete_store(username=payload.username)
    return {"is_success": success}
