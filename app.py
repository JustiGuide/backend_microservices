from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from notifier_module.notifier_api import app as notifier_api
from user_manager.users_api import app as user_api

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(notifier_api)
app.include_router(user_api)


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8008
    uvicorn.run("app:app", host=host, port=port, reload=True)
