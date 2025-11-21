from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from court_listener.listener_api import app as listener_api
from crawler_rag.rag_api import app as rag_api
from lob_delivery.lob_api import app as lob_api
from post_crawler.crawler_api import app as crawler_api
from uscis_handler.uscis_api import app as uscis_api


app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listener_api)
app.include_router(rag_api)
app.include_router(lob_api)
app.include_router(crawler_api)
app.include_router(uscis_api)

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8009
    uvicorn.run("app:app", host=host, port=port, reload=True)
