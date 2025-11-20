from datetime import datetime, timedelta, timezone, date
import io
import os
from typing import Union, Literal
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, HttpUrl, ValidationError
from database import Functions
from authorization import Authorizer, Certificates, DateString, Experiences, GoogleToken, PersonnelDetailsUnion, PersonnelType, PhoneNumber
from email_gateway import Email
from helpers import Helpers
from documents_gateway import DocumentsGateway
from PIL import Image
from scheduler import TaskScheduler

db_func = Functions()
app = APIRouter()
auth = Authorizer()
utils = Helpers()
docs = DocumentsGateway()
scheduler = TaskScheduler()

UserType = Literal["immigrant", "lawpersonnel", "external"]
LawPersonnelType = Literal["lawyer", "nonlawyer", "paralegal", "lawstudent"]

class RetrieveUser(BaseModel):
    parameter: Union[str, EmailStr]

@app.post("/user/{user_type}/get-user")
async def retrieve_user(payload: RetrieveUser, user_type: UserType):
    if user_type == "immigrant":
        return JSONResponse(db_func.get_immigrant(payload.parameter))
    elif user_type == "lawpersonnel":
        return JSONResponse(db_func.get_lawpersonnel(payload.parameter))
    else:
        return JSONResponse(db_func.get_external_lawyer(payload.parameter))

class ImmigrantEmail(BaseModel):
    immigrant_email: EmailStr


@app.post("/user/immigrant/get-kyc")
async def retrieve_immigrant_kyc(payload: ImmigrantEmail):
    immigrant_kyc = db_func.retrieve_immigrant_kyc(immigrant_email=payload.immigrant_email)
    return JSONResponse(immigrant_kyc)


@app.post("/user/immigrant/check-kyc")
async def check_immigrant_kyc(payload: ImmigrantEmail):
    immigrant_kyc = db_func.retrieve_immigrant_kyc(
        immigrant_email=payload.immigrant_email
    )
    if immigrant_kyc != {}:
        immigrant_kyc["exists"] = True
        return immigrant_kyc
    return {"exists": False}

class AddImmigrantKYC(BaseModel):
    immigrant_email: EmailStr
    kyc_data: dict

@app.post("/user/immigrant/add-kyc")
async def add_new_immigrant_kyc(payload: AddImmigrantKYC):
    db_func.update_immigrant_kyc(immigrant_email=payload.immigrant_email, kyc_details=payload.kyc_data)
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    response = db_func.delete_notification(
        immigrant.email,
        "kyc",
        content="Fill the KYC, to get targetted AI responses and lawyer recommendations",
    )
    Helpers.initiate_lawyer_recommendation(payload.immigrant_email)
    return {"successful": True, "notif_comment": response}

@app.post("/user/immigrant/reduce-chat-limit")
async def reduce_chat_limit(payload: ImmigrantEmail):
    db_func.reduce_user_limit(payload.immigrant_email)

class LawpersonnelEmail(BaseModel):
    lawpersonnel_email: EmailStr


@app.post("/user/{lawpersonnel_type}/retrieve-verification-items")
async def retrieve_verification_items(payload: LawpersonnelEmail, lawpersonnel_type: LawPersonnelType):
    verification_items = db_func.get_lawpersonnel_verification_items(lawpersonnel_email=payload.lawpersonnel_email, lawpersonnel_type=lawpersonnel_type)
    return JSONResponse(verification_items)

@app.post("/user/lawpersonnel/verify-lawpersonnel")
async def verify_lawpersonnel(payload: LawpersonnelEmail):
    db_func.verify_lawpersonnel(payload.lawpersonnel_email)

@app.post("/user/{lawpersonnel_type}/delete-verification-items")
async def remove_verification_items(payload: LawpersonnelEmail, lawpersonnel_type: LawPersonnelType):
    db_func.delete_lawpersonnel_verification_items(lawpersonnel_email=payload.lawpersonnel_email, lawpersonnel_type=lawpersonnel_type)


@app.post("/user/{lawpersonnel_type}/delete-info")
async def remove_lawpersonnel_details(
    payload: LawpersonnelEmail, lawpersonnel_type: LawPersonnelType
):
    db_func.delete_lawpersonnel_info(payload.lawpersonnel_email, lawpersonnel_type)


@app.post("/user/lawpersonnel/restart-lawpersonnel")
async def reset_lawpersonnel_profile(payload: LawpersonnelEmail):
    db_func.delete_lawpersonnel(payload.lawpersonnel_email)

@app.post("/user/lawpersonnel/retrieve-verified")
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

@app.post("/user/immigrant/update-info")
async def update_immigrant_profile(payload: ImmigrantUpdate):
    db_func.update_immigrant_data(immigrant_email=payload.immigrant_email, first_name=payload.first_name, profile_picture_url=payload.profile_picture_url, last_name=payload.last_name, full_legal_name=payload.full_legal_name, user_location=payload.user_location)


class LawPersonnelUpdate(BaseModel):
    lawpersonnel_email: EmailStr
    first_name: str = None
    last_name: str = None
    full_legal_name: str = None
    professional_address: str = None
    profile_picture_url: str = None

@app.post("/user/lawpersonnel/update-info")

async def update_lawpersonnel_profile(payload: LawPersonnelUpdate):
    db_func.update_lawpersonnel_data(
        immigrant_email=payload.lawpersonnel_email,
        first_name=payload.first_name,
        profile_picture_url=payload.profile_picture_url,
        last_name=payload.last_name,
        full_legal_name=payload.full_legal_name,
        professional_address=payload.professional_address,
    )


@app.post("/user/{user_type}/check-user")
async def check_user(payload: UserEmail, user_type: UserType):
    user = db_func.get_immigrant(payload.user_email) if user_type == "immigrant" else db_func.get_lawpersonnel(payload.user_email)
    if user :
        return {"exists": True}
    return {"exists": False}

class SubUpdate(BaseModel):
    user_email: EmailStr
    user_tier: str


@app.post("/user/{user_type}/update-subscription")
async def update_user_subscription(payload: SubUpdate, user_type: UserType):
    db_func.update_user_subscription(email=payload.user_email, subscription_type=payload.user_tier)


@app.post("/user/external/remove-user")
async def remove_external_lawyer(payload: UserEmail):
    db_func.remove_external_lawyer(payload.user_email)

class LawyerStatUpdate(BaseModel):
    lawpersonnel_email: EmailStr
    stat_type: str

@app.post("/user/lawpersonnel/update-statistic")
async def update_lawyer_stat(payload: LawyerStatUpdate):
    db_func.update_lawyer_stat(lawyer_email=payload.lawpersonnel_email, stat_type=payload.stat_type)

class ImmigrantVerificationCode(BaseModel):
    immigrant_email: EmailStr
    code: str = None

@app.post("/user/immigrant/add-verification-code")
async def add_immigrant_verification(payload: ImmigrantVerificationCode):
    db_func.add_user_verification(email=payload.immigrant_email, verification_code=payload.code)


@app.post("/user/immigrant/enter-verification-code")
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

@app.post("/user/immigrant/verify-login")
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


@app.post("/user/lawpersonnel/verify-login")
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


@app.post("/user/immigrant/decode-google-token")
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


@app.post("/user/immigrant/verify-google-login")
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

@app.post("/user/{user_type}/verify-password")
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

@app.post("/user/{user_type}/initiate-password-reset")
async def reset_user_password(payload: UserEmail, user_type: UserType):
    db_func.reset_immigrant_password(payload.user_email) if user_type == "immigrant" else db_func.reset_lawpersonnel_password(payload.user_email)

class ModifyPassword(BaseModel):
    user_email: EmailStr
    new_password: str
    old_password: str = "reset"

@app.post("/user/{user_type}/change-password")
@app.post("/user/{user_type}/update-password")
async def modify_user_password(payload: ModifyPassword, user_type: UserType):
    (
        db_func.modify_immigrant_password(
            payload.user_email, payload.old_password, payload.new_password
        )
        if user_type == "immigrant"
        else db_func.modify_lawpersonnel_password(
            payload.user_email, payload.old_password, payload.new_password
        )
    )

class UsernameCheck(BaseModel):
    username: str
    email_id: EmailStr


@app.post("/user/{user_type}/retrieve-username")
async def retrieve_user_username(payload: UsernameCheck, user_type: UserType):
    user = (
        db_func.get_immigrant(payload.username)
        if user_type == "immigrant"
        else db_func.get_lawpersonnel(payload.username)
    )
    if user and user.email != payload.email_id.lower():
        return {"exists": True}
    else:
        return {"exists": False}


@app.post("/user/{user_type}/upload-profile-picture")
async def upload_user_profile_pic(
    user_type: UserType,
    profile_pic: UploadFile = File(...),
    user_email: EmailStr = Form(...)
):
    user = db_func.get_immigrant(user_email) if user_type == "immigrant" else db_func.get_lawpersonnel(user_email)
    try:
        profile_pic_data = await profile_pic.read()
        profile_pic_url = docs.upload_new_profile_picture(profile_pic_data, f"{user_type}s")
        pic_id = Helpers.store_file(
            file=profile_pic,
            file_url=profile_pic_url,
            email_id=user.email,
            filename="user.png",
            readable=True,
        )
        return {
            "resp": True,
            "url": f"{os.getenv('BACKEND')}image/{pic_id}/user.png",
            "error": "No Error",
        }
    except Exception as e:
        return HTTPException(
            status_code=404, detail=f"Error uploading profile picture: {str(e)}"
        )

@app.post("/user/{user_type}/retrieve-profile-picture")
async def retrieve_user_profile_pic(payload: UserEmail, user_type: UserType):
    user = db_func.get_immigrant(payload.user_email) if user_type == "immigrant" else db_func.get_lawpersonnel(payload.user_email)
    if user:
        return {"result": True, "profilePic": user.profile_pic}
    return {"result": False}

@app.post("/user/immigrant/refresh-invitations")
async def refresh_invitations(payload: ImmigrantEmail):
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    retVal: dict[str, Union[list[str], bool]] = {
        "invited": False,
        "lawyer_names": [],
        "lawyer_emails": [],
        "lawyer_images": [],
    }

    immigrant_location = ""
    if immigrant:
        utils.initiate_autofill_generation(immigrant.username)
        utils.initiate_lawyer_recommendation(immigrant.email)
        utils.initiate_rag_update(immigrant.username)

        if (
            immigrant.location is not None
            and immigrant.location.strip() != immigrant_location
        ):
            immigrant_location = immigrant.location

        sub_tier, checkout_id, sub_id = db_func.retrieve_subscription_details(
            user_email=immigrant.email
        )
        invited_lawyer_details = db_func.retrieve_invitation_data(
            invited_type="invited_client", invited_email=immigrant.email
        )

        if invited_lawyer_details is not None:
            for lawyer_email, _ in invited_lawyer_details.items():
                lawyer = db_func.get_lawpersonnel(lawyer_email)
                if lawyer:
                    retVal["invited"] = True
                    retVal["lawyer_names"].append(f"{lawyer.full_legal_name}")
                    retVal["lawyer_emails"].append(lawyer.email)
                    retVal["lawyer_images"].append(lawyer.profile_picture)

        db_func.delete_invitation_data(
            invited_type="refered_user", invited_email=immigrant.email
        )
        db_func.add_user_tracking(user_email=immigrant.email)
        if sub_tier != immigrant.subscription_type:
            db_func.update_subscription_details(
                user_email=immigrant.email,
                sub_tier=immigrant.subscription_type,
                checkout_id=checkout_id,
                sub_id=sub_id,
            )
        return JSONResponse(retVal)
    else:
        return HTTPException(status_code=404, detail="User not found.")


@app.post("/user/{lawpersonnel_type}/retrieve-info")
async def retrieve_lawpersonnel_info(
    payload: LawpersonnelEmail, lawpersonnel_type: LawPersonnelType
):
    lawpersonnel = db_func.get_lawpersonnel(payload.lawpersonnel_email)
    lawpersonnel_docs = db_func.get_lawpersonnel_verification_items(
        lawpersonnel_email=lawpersonnel.email, lawpersonnel_type=lawpersonnel_type
    )
    lawpersonnel_info = lawpersonnel.extract_data()
    lawpersonnel_info["verification_docs"] = lawpersonnel_docs
    if lawpersonnel_type != "lawyer":
        certificates = db_func.get_lawpersonnel_certificates(
            lawpersonnel_email=payload.lawpersonnel_email,
            lawpersonnel_type=lawpersonnel_type,
        )
        lawpersonnel_info["certificates"] = certificates
        experiences = db_func.get_lawpersonnel_experiences(
            lawpersonnel_email=payload.lawpersonnel_email,
            lawpersonnel_type=lawpersonnel_type,
        )
        lawpersonnel_info["experiences"] = experiences
    return JSONResponse(lawpersonnel_info)


@app.post("/user/immigrant/create-account")
async def create_immigrant_account(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    email: EmailStr = Form(...),
    firstName: str = Form(...),
    password: str = Form(...),
    fullLegalName: str = Form(...),
    signature_file: UploadFile = File(...),
    contact_number: PhoneNumber = Form(None),
    date_of_birth: DateString = Form(None),
    lastName: str = Form(None),
    user_location: str = Form(None),
    profilePic: HttpUrl = Form(
        "https://doloreschatbucket.s3.us-east-2.amazonaws.com/icons/users/user.png"
    ),
    profileFile: UploadFile = Form(None),
    data_collection: bool = Form(True),
    receive_emails: bool = Form(True),
):
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host
    x_forwarded_for = request.headers.get("x-forwarded-for")
    upload_info = {
        "user_agent": user_agent,
        "client_ip": client_ip,
        "x_forwarded_for": x_forwarded_for,
    }
    if signature_file is not None and "blob" not in signature_file.filename:
        sign_data = await signature_file.read()
        background_tasks.add_task(
            run_in_threadpool,
            Helpers.sign_saving,
            upload_info=upload_info,
            sign_data=sign_data,
            email=email.lower(),
        )
    db = db_func.Session()
    immigrant = db_func.get_immigrant(email)
    if immigrant and immigrant.hashed_password is not None:
        db.close()
        return HTTPException(status_code=401, detail="User already exists")
    else:
        username = db_func.generate_immigrant_username(email.lower())
        docs.create_directory(username, "immigrants")
        if profileFile is not None and "blob" not in profileFile.filename:
            file_data = await profileFile.read()
            image = Image.open(io.BytesIO(file_data))
            cropped_image: Image.Image = Helpers.resize_thumbnail(image, (175, 175))
            png_data = io.BytesIO()
            cropped_image.save(png_data, format="PNG")
            png_data.seek(0)
            pic_url = docs.upload_new_profile_picture(png_data, user_type="immigrants", username=username)
            db_func.update_user_profile_pic(email, pic_url)
            pic_id = utils.store_file(
                file=profileFile,
                file_url=pic_url,
                email_id=email,
                filename="user.png",
                readable=True,
            )
            profilePic = f"{os.getenv('BACKEND')}image/{pic_id}/user.png"
        referer_email = db_func.retrieve_invitation_data(
            invited_type="refered_user", invited_email=email.lower()
        )
        if fullLegalName is None or fullLegalName == "":
            fullLegalName = f"{firstName} {lastName}".strip()
        if referer_email is not None:
            referer_user = db_func.get_immigrant(referer_email)
            if referer_user.subscription_type.lower() in ["free", "pay"]:
                referer_user.chat_limit += 10
                referer_user.subscription_type = "pay"
                db.commit()
                db.refresh(referer_user)
            db_func.add_notification(
                receiver=referer_user.email,
                sender=email,
                type="connection",
                content=f"Refered user {fullLegalName} has joined JustiGuide",
                target_id={},
            )
        db_func.add_new_user(
            username=username,
            email=email,
            first_name=firstName,
            full_legal_name=fullLegalName,
            last_name=lastName,
            location=user_location,
            password=password,
            profile_pic_url=str(profilePic),
            data_collection=data_collection,
            receive_emails=receive_emails,
            contact_number=contact_number,
            date_of_birth=date_of_birth,
        )
        db_func.add_notification(
            receiver=email,
            sender=email,
            type="kyc",
            content="Fill the KYC, to get targetted AI responses and lawyer recommendations",
            target_id={},
            one_time=True,
        )
        db_func.delete_invitation_data(invited_type="refered_user", invited_email=email)

        access_token = auth.create_access_token(data={"sub": username})
        refresh_token = auth.create_refresh_token(data={"sub": username})
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
        db.close()
        return {
            "success": True,
            "username": username,
            "firstName": firstName,
            "lastName": lastName,
            "fullLegalName": fullLegalName,
            "email": email,
            "profilePicUrl": profilePic,
            "user_location": user_location,
            "receipt_number": "",
            "kyc_bool": False,
        }


@app.post("/user/lawpersonnel/create-account")
async def create_lawpersonnel_account(
    request: Request,
    background_tasks: BackgroundTasks,
    personnel_type: PersonnelType = Form(...),
    details: PersonnelDetailsUnion = Depends(Authorizer.get_typed_details),
    government_id: UploadFile = File(...),
    certificate_documents: list[UploadFile] = File(...),
    experiences: Experiences = Form(...),
    certificates: Certificates = Form(...),
    lawpersonnel_sign: UploadFile = File(...),
    profile_picture: UploadFile = File(...),
    professional_licenses: UploadFile = File(...),
    address_proofs: UploadFile = File(...),
):
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host
    x_forwarded_for = request.headers.get("x-forwarded-for")
    upload_info = {
        "user_agent": user_agent,
        "client_ip": client_ip,
        "x_forwarded_for": x_forwarded_for,
    }
    data_dict = details.model_dump()
    user = db_func.get_lawpersonnel(data_dict["email"])
    retVal = {"status": ""}
    if not user:
        retVal["status"] = "new"
        background_tasks.add_task(
            run_in_threadpool,
            utils.background_new_lawpersonnel,
            upload_info=upload_info,
            data_dict=data_dict,
            personnel_type=personnel_type,
            experiences=experiences,
            certificates=certificates,
            certificate_documents=certificate_documents,
            profile_picture=profile_picture,
            lawpersonnel_sign=lawpersonnel_sign,
            government_id=government_id,
            professional_licenses=professional_licenses,
            address_proofs=address_proofs,
        )
        # Get Expedient Data
        personnel_email = data_dict["email"]
        personnel_name = f"{data_dict['firstName']} {data_dict['lastName']}"
        try:
            Email.send_signup_email(
                personnel_name,personnel_email,"lawpersonnel"
            )
            print(f"{personnel_name}'s Welcome Email Sent Successfully.")
        except Exception as exp:
            print(f"Email Not Sent Exception Occurred: {exp}.")
    else:
        retVal["status"] = "old"
        utils.update_lawyer_to_team(user)
        if not user.verified:
            schedule_date = datetime.now(timezone.utc) + timedelta(days=1)
            scheduler.schedule_task(
                utils.background_lawpersonnel_verification, schedule_date, user=user
            )
    return JSONResponse(retVal)


# TODO: May not be required
# @app.post("/user/lawpersonnel/verify-license")
# @app.post("/user/lawpersonnel/verify-id")


@app.post("/user/lawpersonnel/statistics/connection-requests/growth")
async def get_conn_req_growth(payload: UserEmail):
    growth_details = db_func.get_lawyer_stat_nums(
        lawyer_email=payload.user_email, stat_type="conn_req"
    )
    difference = growth_details[0] - growth_details[1]
    growthBool = True
    if difference < 0:
        growthBool = False
        difference = difference * (-1)
    growth_val = (
        (difference / growth_details[1]) * 100 if growth_details[1] > 0 else 100.00
    )
    growth = growth_val
    return {
        "metric": growth_details[0],
        "growth": str(growth),
        "isPositive": growthBool,
    }


@app.post("/user/lawpersonnel/statistics/clients/growth")
async def get_client_growth(payload: UserEmail):
    growth_details = db_func.get_lawyer_stat_nums(
        lawyer_email=payload.user_email, stat_type="client_num"
    )
    difference = growth_details[0] - growth_details[1]
    growthBool = True
    if difference < 0:
        growthBool = False
        difference = difference * (-1)
    growth_val = (
        (difference / growth_details[1]) * 100 if growth_details[1] > 0 else 100.00
    )
    growth = growth_val
    return {
        "metric": growth_details[0],
        "growth": str(growth),
        "isPositive": growthBool,
    }


@app.post("/user/lawpersonnel/statistics/clients")
async def get_client_statistics(payload: UserEmail):
    stat = db_func.get_lawyer_stats(payload.user_email, "client_num")
    return JSONResponse(utils.reformat_data(stat))


@app.post("/user/lawpersonnel/statistics/assignee/growth")
async def get_assignee_growth(payload: UserEmail):
    growth_details = db_func.get_lawyer_stat_nums(
        lawyer_email=payload.user_email, stat_type="assignee_num"
    )
    difference = growth_details[0] - growth_details[1]
    growthBool = True
    if difference < 0:
        growthBool = False
        difference = difference * (-1)
    growth_val = (
        (difference / growth_details[1]) * 100 if growth_details[1] > 0 else 100.00
    )
    growth = growth_val
    return {
        "metric": growth_details[0],
        "growth": str(growth),
        "isPositive": growthBool,
    }


@app.post("/user/lawpersonnel/statistics/submitted/applications")
async def get_appl_statistics(payload: UserEmail):
    stat = db_func.get_lawyer_stats(payload.user_email, "submitted_appl")
    return JSONResponse(utils.reformat_data(stat))


@app.post("/user/lawpersonnel/statistics/submitted/applications/growth")
async def get_appl_growth(payload: UserEmail):
    growth_details = db_func.get_lawyer_stats(payload.user_email, "submitted_appl")
    difference = growth_details[0] - growth_details[1]
    growthBool = True
    if difference < 0:
        growthBool = False
        difference = difference * (-1)
    growth_val = (
        (difference / growth_details[1]) * 100 if growth_details[1] > 0 else 100.00
    )
    growth = growth_val
    return {
        "metric": growth_details[0],
        "growth": str(growth),
        "isPositive": growthBool,
    }


@app.post("/user/lawpersonnel/statistics/submitted/documents")
async def get_docs_statistics(payload: UserEmail):
    stat = db_func.get_lawyer_stats(payload.user_email, "submitted_forms")
    return JSONResponse(utils.reformat_data(stat))
