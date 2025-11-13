from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from stripe_gateway.stripe_api import app as stripe_api
from subscription_management.submanagement_api import app as subscription_api
from database import Functions

db_func = Functions()

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CaseSubRetrieval(BaseModel):
    case_ids: list[str]

@app.post("/sub/lawpersonnel/retrieve-cases")
async def retrieve_case_subs(payload: CaseSubRetrieval):
    all_case_subs = db_func.retrieve_lawpersonnel_case_subs(case_ids=payload.case_ids)
    return JSONResponse(all_case_subs)


app.include_router(stripe_api)
app.include_router(subscription_api)


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8002
    uvicorn.run("app:app", host=host, port=port, reload=True)
