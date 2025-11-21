from fastapi import APIRouter
import os
from .rag_application import VectorUpload

app = APIRouter()

@app.get("/rag/update")
async def update_opinions_store():
    # Create Instance
    """
    Add Vector Store Ids and File Paths In Instance Creation,
    If Not, Opinions Store And Files Will Be Used as Default.
    """
    return "Check Back Later."


@app.get("/rag/update-dolores/opinions")
async def rag_update_dolores_relo_opinions():
    vec = VectorUpload(
        vector_store_id=os.getenv("DOLORES_RELO_VECTOR_STORE_ID"), section="opinions"
    )
    return vec.upload


@app.get("/rag/update-dolores/news")
async def rag_update_dolores_relo_news():
    vec = VectorUpload(
        vector_store_id=os.getenv("DOLORES_RELO_VECTOR_STORE_ID"), section="uscis_news"
    )
    return vec.upload
