from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from rag_console.rag_api import app as rag_api

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rag_api)

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8006
    uvicorn.run("app:app", host=host, port=port, reload=True)
