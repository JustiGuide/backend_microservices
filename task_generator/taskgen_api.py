from fastapi.responses import JSONResponse
from .task_generator import TaskManagementAgent
from fastapi import APIRouter
from response_schemas import (
    TeamMember,
    TeamStructure,
    UrgencyFactor,
    LawPersonnelSchema,
)
from pydantic import EmailStr, Field, BaseModel
from database import Functions

generator = TaskManagementAgent()
app = APIRouter()
db_func = Functions()

class TaskGenerationRequest(BaseModel):
    case_type: str
    lawyer: LawPersonnelSchema
    team: list[EmailStr]


class TaskReorderRequest(BaseModel):
    lawpersonnel_email: EmailStr
    case_id: str
    urgency: UrgencyFactor


class TaskDeadlineUpdateRequest(BaseModel):
    tasks: list[str]
    case_description: str
    urgency: UrgencyFactor
    constraints: str = Field(..., description="A free-text description of constraints, e.g., 'Client is traveling from June 10-20. USCIS RFE deadline is July 1st.'")


@app.post("/task-gen/lawpersonnel/generate")
async def generate_tasks(payload: TaskGenerationRequest):
    team = [db_func.get_lawpersonnel(member) for member in payload.team]
    task_list = await generator.generate_task_list(
        case_type=payload.case_type,
        lawyer=payload.lawyer,
        team=team
    )
    return JSONResponse(task_list.generated_tasks)


@app.post("/task-gen/lawpersonnel/reorder")
async def reorder_tasks(payload: TaskReorderRequest):
    all_tasks = db_func.get_tasks(lawpersonnel_email=payload.lawpersonnel_email, case_id=payload.case_id)
    case_details = db_func.get_case_details(
        lawpersonnel_email=payload.lawpersonnel_email, case_id=payload.case_id
    )
    all_members = db_func.get_case_members(
        lawpersonnel_email=payload.lawpersonnel_email, case_id=payload.case_id
    )
    all_members.append(db_func.get_lawpersonnel(payload.lawpersonnel_email))

    team_structure = TeamStructure(
        size=len(all_members),
        members=[
            TeamMember(
                name=member.full_legal_name,
                active_cases=db_func.calculate_active_cases(member.email),
                role=member.personnel_type,
                type=db_func.get_member_permissions(
                    member.email, payload.lawpersonnel_email
                ),
                speciality=member.specialty,
            )
            for member in all_members
        ],
    )
    task_order = await generator.reorder_task_list(
        tasks=all_tasks,
        case_description=case_details.get("case_description"),
        urgency=payload.urgency,
        team_structure=team_structure,
    )
    return JSONResponse(task_order.reordered_tasks)


@app.post("/task-gen/lawpersonnel/update-deadlines")
async def update_deadlines(payload: TaskDeadlineUpdateRequest):
    tasks = [db_func.get_task_details(task) for task in payload.tasks]
    new_tasks =  await generator.update_task_deadlines(
        tasks=tasks,
        case_description=payload.case_description,
        urgency=payload.urgency,
        constraints=payload.constraints
    )
    return JSONResponse(new_tasks.updated_tasks)
