from datetime import datetime, timezone, date
from typing import Union
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, ValidationError
from rdflib import Literal
from database import Functions
from authorization import Authorizer, GoogleToken
from email_gateway import Email

db_func = Functions()
app = APIRouter()
auth = Authorizer()

UserType = Literal["immigrant", "lawpersonnel", "external"]
LawPersonnelType = Literal["lawyer", "nonlawyer", "paralegal", "lawstudent"]

class RetrieveUser(BaseModel):
    parameter: Union[str, EmailStr]

app.post("/user/{user_type}/get-user")
async def retrieve_user(payload: RetrieveUser, user_type: UserType):
    if user_type == "immigrant":
        return JSONResponse(db_func.get_immigrant(payload.parameter))
    elif user_type == "lawpersonnel":
        return JSONResponse(db_func.get_lawpersonnel(payload.parameter))
    else:
        return JSONResponse(db_func.get_external_lawyer(payload.parameter))

class ImmigrantEmail(BaseModel):
    immigrant_email: EmailStr


app.post("/user/immigrant/get-kyc")
async def retrieve_immigrant_kyc(payload: ImmigrantEmail):
    immigrant_kyc = db_func.retrieve_immigrant_kyc(immigrant_email=payload.immigrant_email)
    return JSONResponse(immigrant_kyc)


app.post("/user/immigrant/reduce-chat-limit")
async def reduce_chat_limit(payload: ImmigrantEmail):
    db_func.reduce_user_limit(payload.immigrant_email)

class LawpersonnelEmail(BaseModel):
    lawpersonnel_email: EmailStr


app.post("/user/{lawpersonnel_type}/retrieve-verification-items")
async def retrieve_verification_items(payload: LawpersonnelEmail, lawpersonnel_type: LawPersonnelType):
    verification_items = db_func.get_lawpersonnel_verification_items(lawpersonnel_email=payload.lawpersonnel_email, lawpersonnel_type=lawpersonnel_type)
    return JSONResponse(verification_items)

app.post("/user/lawpersonnel/verify-lawpersonnel")
async def verify_lawpersonnel(payload: LawpersonnelEmail):
    db_func.verify_lawpersonnel(payload.lawpersonnel_email)

app.post("/user/{lawpersonnel_type}/delete-verification-items")
async def remove_verification_items(payload: LawpersonnelEmail, lawpersonnel_type: LawPersonnelType):
    db_func.delete_lawpersonnel_verification_items(lawpersonnel_email=payload.lawpersonnel_email, lawpersonnel_type=lawpersonnel_type)


app.post("/user/{lawpersonnel_type}/delete-info")
async def remove_lawpersonnel_details(
    payload: LawpersonnelEmail, lawpersonnel_type: LawPersonnelType
):
    db_func.delete_lawpersonnel_info(payload.lawpersonnel_email, lawpersonnel_type)


app.post("/user/lawpersonnel/restart-lawpersonnel")
async def reset_lawpersonnel_profile(payload: LawpersonnelEmail):
    db_func.delete_lawpersonnel(payload.lawpersonnel_email)

app.post("/user/lawpersonnel/retrieve-verified")
async def retrieve_verified_lawpersonnel():
    all_lawpersonnel = db_func.retrieve_verified_lawyers()
    return JSONResponse(all_lawpersonnel)

class UserEmail(BaseModel):
    user_email: EmailStr

class ImmigrantUpdate(BaseModel):
    immigrant_email: EmailStr
    first_name: str = None
    last_name: str = None
    full_legal_name: str = None
    user_location: str = None
    profile_picture_url: str = None

app.post("/user/immigrant/update-info")
async def update_immigrant_profile(payload: ImmigrantUpdate):
    db_func.update_immigrant_data(immigrant_email=payload.immigrant_email, first_name=payload.first_name, profile_picture_url=payload.profile_picture_url, last_name=payload.last_name, full_legal_name=payload.full_legal_name, user_location=payload.user_location)


class LawPersonnelUpdate(BaseModel):
    lawpersonnel_email: EmailStr
    first_name: str = None
    last_name: str = None
    full_legal_name: str = None
    professional_address: str = None
    profile_picture_url: str = None

app.post("/user/lawpersonnel/update-info")

async def update_lawpersonnel_profile(payload: LawPersonnelUpdate):
    db_func.update_lawpersonnel_data(
        immigrant_email=payload.lawpersonnel_email,
        first_name=payload.first_name,
        profile_picture_url=payload.profile_picture_url,
        last_name=payload.last_name,
        full_legal_name=payload.full_legal_name,
        professional_address=payload.professional_address,
    )


app.post("/user/{user_type}/check-user")
async def check_user(payload: UserEmail, user_type: UserType):
    user = db_func.get_immigrant(payload.user_email) if user_type == "immigrant" else db_func.get_lawpersonnel(payload.user_email)
    if user :
        return {"exists": True}
    return {"exists": False}

class SubUpdate(BaseModel):
    user_email: EmailStr
    user_tier: str


app.post("/user/{user_type}/update-subscription")
async def update_user_subscription(payload: SubUpdate, user_type: UserType):
    db_func.update_user_subscription(email=payload.user_email, subscription_type=payload.user_tier)


app.post("/user/external/remove-user")
async def remove_external_lawyer(payload: UserEmail):
    db_func.remove_external_lawyer(payload.user_email)

class LawyerStatUpdate(BaseModel):
    lawpersonnel_email: EmailStr
    stat_type: str

app.post("/user/lawpersonnel/update-statistic")
async def update_lawyer_stat(payload: LawyerStatUpdate):
    db_func.update_lawyer_stat(lawyer_email=payload.lawpersonnel_email, stat_type=payload.stat_type)

class ImmigrantVerificationCode(BaseModel):
    immigrant_email: EmailStr
    code: str = None

app.post("/user/immigrant/add-verification-code")
async def add_immigrant_verification(payload: ImmigrantVerificationCode):
    db_func.add_user_verification(email=payload.immigrant_email, verification_code=payload.code)


app.post("/user/immigrant/enter-verification-code")
async def add_immigrant_verification(payload: ImmigrantVerificationCode):
    actual_code = db_func.retrieve_user_verification(email=payload.immigrant_email)
    if actual_code is None:
        raise HTTPException(status_code=404, detail="User not found")
    if actual_code != payload.code:
        raise HTTPException(status_code=401, detail="Invalid verification code")
    db_func.delete_user_verification(payload.immigrant_email)
    return {"success": True}

class LoginInput(BaseModel):
    login_email: EmailStr
    login_pass: str

app.post("/user/immigrant/verify-login")
async def verify_immigrant_login(payload: LoginInput, response: Response):
    immigrant = db_func.get_immigrant(payload.login_email)
    kyc_bool = db_func.retrieve_immigrant_kyc(payload.login_email) != {}
    if immigrant:
        if not kyc_bool:
            db_func.add_notification(
                receiver=immigrant.email,
                sender=immigrant.email,
                type="kyc",
                content="Fill the KYC, to get targetted AI responses and lawyer recommendations",
                target_id={},
                one_time=True,
            )
        if not immigrant.verify_password(payload.login_pass):
            return {"resp": "Incorrect Password"}
        else:
            print()
            access_token = auth.create_access_token(data={"sub": immigrant.username})
            refresh_token = auth.create_refresh_token(data={"sub": immigrant.username})
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,
                samesite="none",
                path="/",
                max_age=60 * 60 * 30,
            )
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="none",
                path="/auth",
                max_age=60 * 60 * 24 * 15,
            )
            return {
                "resp": True,
                "username": immigrant.username,
                "firstName": immigrant.first_name,
                "lastName": immigrant.last_name,
                "fullLegalName": immigrant.full_legal_name,
                "email": immigrant.email,
                "profilePicUrl": immigrant.profile_pic,
                "user_location": immigrant.location,
                "receipt_number": immigrant.receipt_number,
                "kyc_bool": kyc_bool,
            }


app.post("/user/lawpersonnel/verify-login")
async def verify_immigrant_login(payload: LoginInput, response: Response):
    lawpersonnel = db_func.get_lawpersonnel(payload.login_email)
    if lawpersonnel:
        if not lawpersonnel.verified:
            raise HTTPException(status_code=401, detail="Profile is not yet verified")
        if not lawpersonnel.verify_password(payload.login_pass):
            return {"resp": False}
        else:
            team_lawyers, case_lawyers = db_func.new_lawpersonnel_add_team_case(
                lawpersonnel.email, f"{lawpersonnel.full_legal_name}"
            )
            if len(team_lawyers) > 0:
                for lawyer in team_lawyers:
                    db_func.add_notification(
                        receiver=lawyer.email,
                        sender=lawpersonnel.email,
                        type="teams",
                        content=f"{lawpersonnel.full_legal_name} has joined your team",
                        target_id={"team_member": lawpersonnel.email},
                        one_time=True,
                    )
                    db_func.add_notification(
                        receiver=lawpersonnel.email,
                        sender=lawyer.email,
                        type="teams",
                        content=f"{lawyer.full_legal_name} has added you to their team",
                        target_id={},
                    )
            if len(case_lawyers) > 0:
                for case_dets in case_lawyers:
                    db_func.add_notification(
                        receiver=lawpersonnel.email,
                        sender=case_dets["lawyer"].email,
                        type="cases",
                        content=f"{case_dets['lawyer'].full_legal_name} has added you to case #{case_dets['case_id']}",
                        target_id={"case_id": case_dets["case_id"]},
                    )

            access_token = auth.create_access_token(data={"sub": lawpersonnel.username})
            refresh_token = auth.create_refresh_token(
                data={"sub": lawpersonnel.username}
            )
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,
                samesite="none",
                path="/",
                max_age=60 * 60 * 30,
            )
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="none",
                path="/auth",
                max_age=60 * 60 * 24 * 15,
            )
            return {
                "resp": True,
                "username": lawpersonnel.username,
                "firstName": lawpersonnel.firstName,
                "lastName": lawpersonnel.lastName,
                "professionalAddress": lawpersonnel.professional_address,
                "email": lawpersonnel.email,
                "profilePicture": lawpersonnel.profile_picture,
                "subscription": lawpersonnel.subscription_tier,
            }

class GoogleDecode(BaseModel):
    credential: GoogleToken


class GoogleUserInfo(BaseModel):
    email: EmailStr
    name: str
    given_name: str
    family_name: str = None
    picture: str = None


app.post("/user/immigrant/decode-google-token")
async def decode_google_token(payload: GoogleDecode):
    google_access_token = payload.credential
    google_user_info_raw = await Authorizer.validate_google_access_token(google_access_token)

    try:
        google_user_info = GoogleUserInfo(**google_user_info_raw)
        user = db_func.get_immigrant(google_user_info.email.lower())
        if user:
            return {"exists": True}
        return {
            "email": google_user_info.email,
            "full_legal_name": google_user_info.name,
            "first_name": google_user_info.given_name,
            "last_name": google_user_info.family_name,
            "profile_pic": google_user_info.picture,
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


app.post("/user/immigrant/verify-google-login")
async def verify_immigrant_google_login(payload: GoogleDecode, response: Response):
    google_access_token = payload.credential
    google_user_info_raw = await Authorizer.validate_google_access_token(
        google_access_token
    )

    try:
        google_user_info = GoogleUserInfo(**google_user_info_raw)
        print(f"Google user info validated: {google_user_info}")
    except ValidationError as e:
        print(f"Google user info validation failed: {e}")
        return HTTPException(
            status_code=400, detail="Invalid Google account information"
        )

    immigrant = db_func.get_immigrant(google_user_info.email.lower())
    if not immigrant:
        return HTTPException(status_code=404, detail="User not found.")

    kyc_bool = False
    kyc_details = db_func.retrieve_immigrant_kyc(immigrant.email.lower())
    if kyc_details != {}:
        kyc_bool = True

    if not kyc_bool:
        db_func.add_notification(
            receiver=immigrant.email,
            sender=immigrant.email,
            type="kyc",
            content="Fill the KYC, to get targetted AI responses and lawyer recommendations",
            target_id={},
            one_time=True,
        )

    access_token = auth.create_access_token(data={"sub": immigrant.username})
    refresh_token = auth.create_refresh_token(data={"sub": immigrant.username})

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=60 * 60 * 30,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/auth",
        max_age=60 * 60 * 24 * 15,
    )

    return {
        "resp": True,
        "username": immigrant.username,
        "firstName": immigrant.first_name,
        "lastName": immigrant.last_name,
        "fullLegalName": immigrant.full_legal_name,
        "email": immigrant.email,
        "profilePicUrl": immigrant.profile_pic,
        "user_location": immigrant.location,
        "receipt_number": immigrant.receipt_number,
        "kyc_bool": kyc_bool,
    }

app.post("/user/{user_type}/verify-password")
async def verify_user_password(payload: LoginInput, user_type: UserType):
    user = (
        db_func.get_immigrant(payload.login_email)
        if user_type == "immigrant"
        else db_func.get_lawpersonnel(payload.login_email)
    )
    if user:
        if user.verify_password(payload.login_pass):
            return {"check": True}
    return {"check": False}

app.post("/user/{user_type}/initiate-password-reset")
app.post("/user/{user_type}/change-password")
app.post("/user/{user_type}/update-password")
app.post("/user/{user_type}/upload-profile-picture")
app.post("/user/lawpersonnel/verify-license")
app.post("/user/lawpersonnel/verify-id")
app.post("/user/lawpersonnel/retrieve-profile-picture")
app.post("/user/{user_type}/retrieve-username")
app.post("/user/immigrant/refresh-invitations")
app.post("/user/immigrant/check-kyc")
app.post("/user/immigrant/add-kyc")
app.post("/user/{lawpersonnel_type}/retrieve-info")
app.post("/user/immigrant/create-account")
app.post("/user/lawpersonnel/create-account")
app.post("/user/lawpersonnel/statistics/connection-requests/growth")
app.post("/user/lawpersonnel/statistics/clients/growth")
app.post("/user/lawpersonnel/statistics/clients")
app.post("/user/lawpersonnel/statistics/assignee/growth")
app.post("/user/lawpersonnel/statistics/submitted/applications")
app.post("/user/lawpersonnel/statistics/submitted/applications/growth")
app.post("/user/lawpersonnel/statistics/submitted/documents")
def temp():
    pass
