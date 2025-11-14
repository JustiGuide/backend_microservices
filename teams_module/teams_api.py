
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from email_gateway import Email
from database import Functions
from authorization import (
    MemberPermissions,
    LawyerCaseID,
    MemberEmail,
)
from helpers import Helpers
from scheduler import TaskScheduler

db_func = Functions()
app = APIRouter()
scheduler = TaskScheduler()

class AddCaseTeammate(BaseModel):
    lawpersonnel_email: EmailStr
    case_id: LawyerCaseID
    member_email: EmailStr
    member_first_name: str
    member_last_name: str
    member_permissions: MemberPermissions

@app.post("/teams/lawpersonnel/case/add-teammate")
async def add_case_teammate(payload: AddCaseTeammate):
    member = db_func.get_lawpersonnel(payload.member_email)
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    if member:
        db_func.add_case_teammate(
            lawyer_email=lawpersonnel.email,
            case_id=payload.case_id,
            member_name=member.full_legal_name,
            member_email=member.email
        )
        Helpers.add_notification(
            receiver=member.email,
            sender=lawpersonnel.email,
            type="cases",
            content=f"{lawpersonnel.full_legal_name} has added you to case #{payload.case_id}",
            target_id={"case_id": payload.case_id},
        )
    else:
        Email.send_team_invitation(inviting_lawpersonnel=lawpersonnel, invited_lawpersonnel_email=payload.member_email, invited_lawpersonnel_name=f"{payload.member_first_name} {payload.member_last_name}")
        db_func.add_invitation(
            invited_type="invite_to_case",
            invited_email=payload.member_email,
            invitee_email=lawpersonnel.email,
            member_permissions=payload.member_permissions,
            case_id=payload.case_id,
        )

class RemoveCaseTeammate(BaseModel):
    lawpersonnel_email: EmailStr
    case_id: LawyerCaseID
    member_email: MemberEmail

class CaseTeamRetrievalInput(BaseModel):
    lawpersonnel_email: EmailStr
    case_id: LawyerCaseID

@app.post("/teams/lawpersonnel/case/remove-teammate")
async def remove_case_teammate(payload: RemoveCaseTeammate):
    db_func.remove_case_member(lawyer_email=payload.lawpersonnel_email, case_id=payload.case_id, member_email=payload.member_email)

@app.post("/teams/lawpersonnel/case/retrieve-team")
async def retrieve_case_team(payload: CaseTeamRetrievalInput):
    result = db_func.get_case_team(payload.lawpersonnel_email, payload.case_id)
    for member_email in result:
        member = db_func.get_lawpersonnel(member_email)
        result[member_email]["profile_pic_url"] = member.profile_picture
    
    return JSONResponse(result)


@app.post("/teams/lawpersonnel/org/add-member")
async def add_org_member(payload: AddCaseTeammate):
    member = db_func.get_lawpersonnel(payload.member_email)
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    if member:
        db_func.add_team_member(
            lawpersonnel.email,
            member.email,
            member.personnel_type.capitalize(),
            payload.member_permissions,
        )
    else:        
        Email.send_team_invitation(inviting_lawpersonnel=lawpersonnel, invited_lawpersonnel_email=payload.member_email, invited_lawpersonnel_name=f"{payload.member_first_name} {payload.member_last_name}")
        db_func.add_invitation(
            invited_type="invited_to_team",
            invited_email=member.email,
            invitee_email=lawpersonnel.email,
            member_role=member.personnel_type.capitalize(),
            member_permissions=payload.member_permissions,
        )

class OrgMemberRetrieval(BaseModel):
    lawpersonnel_email: EmailStr

@app.post("/teams/lawpersonnel/org/retrieve-members")
async def retrieve_org_members(payload: OrgMemberRetrieval):
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    teammates = db_func.retrieve_team_members(lawyer_email=lawpersonnel.email)
    result = []
    for member_email in teammates:
        member = db_func.get_lawpersonnel(member_email)
        teammates[member_email]["email"] = member_email
        if member:
            teammates[member_email]["username"] = member.username
            teammates[member_email]["name"] = member.full_legal_name
            teammates[member_email]["profilePicUrl"] = member.profile_picture
            teammates[member_email]["address"] = member.professional_address
            teammates[member_email]["speciality"] = member.specialty
        else:
            teammates[member_email]["username"] = ""
            teammates[member_email]["name"] = ""
            teammates[member_email]["profilePicUrl"] = ""
            teammates[member_email]["address"] = ""
            teammates[member_email]["speciality"] = ""
        result.append(teammates[member_email])
    return JSONResponse(result)

class OrgMemberEdit(BaseModel):
    lawpersonnel_email: EmailStr
    member_email: MemberEmail
    member_permission: MemberPermissions

@app.post("/teams/lawpersonnel/org/edit-member")
async def edit_org_members(payload: OrgMemberEdit):
    db_func.edit_team_members(lawyer_email=payload.lawpersonnel_email, member_email=payload.member_email, new_permissions=payload.member_permission)

