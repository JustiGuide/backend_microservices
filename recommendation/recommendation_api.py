from fastapi import APIRouter, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import Functions
from .recommendation_agent import Recommender
from background_utility import BackgroundUtilities


db_func = Functions()
app = APIRouter()
recommender = Recommender()

class UsernameInput(BaseModel):
    username: str

@app.post("/recommender/immigrant/get-recommended")
async def get_recommended(payload: UsernameInput, background_tasks: BackgroundTasks):
    immigrant = db_func.get_immigrant(payload.username)
    (
        preRec_regLawyers,
        preRec_unregLawyers,
        preRec_dummyLawyers,
        pending_regLawyers,
        invited_unregLawyers,
        _,
    ) = recommender.presort_lawyers(immigrant)
    if recommender._to_generate(preRec={"registered": [regLawyer["email"] for regLawyer in preRec_regLawyers], "unregistered": [unregLawyer["email"] for unregLawyer in preRec_unregLawyers]}):
        background_tasks.add_task(
            run_in_threadpool,
            BackgroundUtilities.start_recommender,
            immigrant=immigrant,
            force=True,
        )
        return {"success": False}
    else:
        recLawyers = db_func.get_lawyer_recommendations(immigrant.email)
        numRec = 3
        iMax = jMax = numRec - 1
        if len(preRec_regLawyers) < numRec:
            iMax = 0
        if len(preRec_unregLawyers) < numRec:
            jMax = 0

        if recLawyers == {"registered": [], "unregistered": []}:
            recLawyers["registered"] = [
                preRec_regLaw["email"] for preRec_regLaw in preRec_regLawyers
            ]
            recLawyers["unregistered"] = [
                preRec_unregLaw["email"] for preRec_unregLaw in preRec_unregLawyers
            ]
        recommended_lawyers = {}
        for i, reglawyer_email in enumerate(recLawyers["registered"]):
            if reglawyer_email != "":
                lawyer = db_func.get_lawpersonnel(reglawyer_email)
                recBool = False
                if i <= iMax:
                    recBool = True
                recommended_lawyers[lawyer.username] = {
                    "Point of Contact": f"{lawyer.full_legal_name}",
                    "Law Firm Name": lawyer.law_firm_name,
                    "Experience": lawyer.experience,
                    "Expertise": lawyer.specialty,
                    "Main Office": lawyer.professional_address,
                    "Phone Number": lawyer.contact_number,
                    "Image link": lawyer.profile_picture,
                    "Email Address": lawyer.email,
                    "pending": False,
                    "type": "internal",
                    "recommended": recBool,
                }
        for j, unreglawyer_username in enumerate(recLawyers["unregistered"]):
            if unreglawyer_username != "":
                ext_lawyer = db_func.get_external_lawyer(unreglawyer_username)
                recBool = False
                if j <= jMax:
                    recBool = True
                if ext_lawyer:
                    recommended_lawyers[ext_lawyer.username] = {
                        "Point of Contact": ext_lawyer.fullName,
                        "Law Firm Name": ext_lawyer.lawFirmName,
                        "Experience": ext_lawyer.experience,
                        "Expertise": ext_lawyer.expertise,
                        "Main Office": ext_lawyer.professionalAddress,
                        "Phone Number": ext_lawyer.contactNumber,
                        "Image link": ext_lawyer.profilePicture,
                        "Email Address": ext_lawyer.email,
                        "pending": False,
                        "type": "external",
                        "recommended": recBool,
                    }
        all_lawyers = {
            "success": True,
            **recommended_lawyers,
            **preRec_dummyLawyers,
            **pending_regLawyers,
            **invited_unregLawyers,
        }
        return JSONResponse(all_lawyers)


@app.post("/recommender/immigrant/get-lawyers")
async def get_lawyers(payload: UsernameInput):
    immigrant = db_func.get_immigrant(payload.username)
    (
        preRec_regLawyers,
        preRec_unregLawyers,
        preRec_dummyLawyers,
        pending_regLawyers,
        invited_unregLawyers,
        _,
    ) = recommender.presort_lawyers(immigrant)
    regLawyers = {}
    unregLawyers = {}
    for lawyer_dets in preRec_regLawyers:
        lawyer = db_func.get_lawpersonnel(lawyer_dets["username"])
        regLawyers[lawyer.username] = {
            "Point of Contact": f"{lawyer.full_legal_name}",
            "Law Firm Name": lawyer.law_firm_name,
            "Experience": lawyer.experience,
            "Expertise": lawyer.specialty,
            "Main Office": lawyer.professional_address,
            "Phone Number": lawyer.contact_number,
            "Image link": lawyer.profile_picture,
            "Email Address": lawyer.email,
            "pending": False,
            "type": "internal",
            "recommended": False,
        }
    for extLawyer_dets in preRec_unregLawyers:
        ext_lawyer = db_func.get_external_lawyer(extLawyer_dets["username"])
        if ext_lawyer:
            unregLawyers[ext_lawyer.username] = {
                "Point of Contact": ext_lawyer.fullName,
                "Law Firm Name": ext_lawyer.lawFirmName,
                "Experience": ext_lawyer.experience,
                "Expertise": ext_lawyer.expertise,
                "Main Office": ext_lawyer.professionalAddress,
                "Phone Number": ext_lawyer.contactNumber,
                "Image link": ext_lawyer.profilePicture,
                "Email Address": ext_lawyer.email,
                "pending": False,
                "type": "external",
                "recommended": False,
            }
    all_lawyers = {
        **regLawyers,
        **unregLawyers,
        **preRec_dummyLawyers,
        **pending_regLawyers,
        **invited_unregLawyers,
    }
    return JSONResponse(all_lawyers)

