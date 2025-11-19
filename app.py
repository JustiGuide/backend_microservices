from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from connection_manager.connection_api import app as conn_api
from intake_module.intakes_api import app as intake_api


app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(conn_api)
app.include_router(intake_api)


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8007
    uvicorn.run("app:app", host=host, port=port, reload=True)
