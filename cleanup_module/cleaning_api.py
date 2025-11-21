from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from .cleaner import CaseDeletion, DisconnectLawyer, DeleteImmigrant, DeleteLawpersonnel

app = APIRouter()
case_del = CaseDeletion()
disc_lawyer =DisconnectLawyer()
del_immigrant = DeleteImmigrant()

class LawPersonnelCleanup(BaseModel):
    lawpersonnel_username: str

class ImmigrantCleanup(BaseModel):
    immigrant_email: EmailStr

class CaseCleanup(BaseModel):
    lawpersonnel_email: EmailStr
    case_id: str

class LawyerDisconnection(BaseModel):
    lawpersonnel_email: EmailStr
    immigrant_email: EmailStr

@app.post("/cleanup/lawpersonnel/delete-case")
async def delete_lawpersonnel_case(payload: CaseCleanup):
    case_del.delete_case(lawyer_email=payload.lawpersonnel_email, case_id=payload.case_id)

@app.post("/cleanup/immigrant/disconnect-lawyer")
async def disconnect_lawpersonnel(payload: LawyerDisconnection):
    disc_lawyer.disconnect_lawyer(lawyer_email=payload.lawpersonnel_email, immigrant_email=payload.immigrant_email)

@app.post("/cleanup/immigrant/delete-me")
async def delete_immigrant(payload: ImmigrantCleanup):
    del_immigrant.delete_immigrant_user(immigrant_email=payload.immigrant_email)

@app.post("/cleanup/lawpersonnel/delete-me")
async def delete_lawpersonnel(payload: LawPersonnelCleanup):
    del_personnel = DeleteLawpersonnel(payload.lawpersonnel_username)
    del_personnel.run_cleanup()

@app.post("/cleanup/lawpersonnel/purge-me")
async def purge_lawpersonnel(payload: LawPersonnelCleanup):
    del_personnel = DeleteLawpersonnel(payload.lawpersonnel_username)
    del_personnel.complete_clean()

@app.post("/cleanup/lawpersonnel/check")
async def check_lawpersonnel_cleanup(payload: LawPersonnelCleanup):
    del_personnel = DeleteLawpersonnel(payload.lawpersonnel_username)
    del_personnel.run_keep_cleanup()
