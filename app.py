from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from cases_module.cases_api import app as cases_api
from tasks_module.tasks_api import app as tasks_api
from teams_module.teams_api import app as teams_api

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases_api)
app.include_router(tasks_api)
app.include_router(teams_api)

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8003
    uvicorn.run("app:app", host=host, port=port, reload=True)
