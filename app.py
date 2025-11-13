from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from stripe_gateway.stripe_api import app as stripe_api
from subscription_management.submanagement_api import app as subscription_api


app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stripe_api)
app.include_router(subscription_api)

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8002
    uvicorn.run("app:app", host=host, port=port, reload=True)
