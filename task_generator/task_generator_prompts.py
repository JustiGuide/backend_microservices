from datetime import date
import json
from pydantic import BaseModel
from database import LawPersonnel
from response_schemas import UrgencyFactor, Task, TaskDeadlineUpdateResponse, TaskGenerationResponse, TaskReorderResponse, TeamStructure


def get_response_schema(model: BaseModel) -> str:
    return json.dumps(model.model_json_schema(), indent=2)


def generate_tasks_prompt(
    case_type: str, lawyer: LawPersonnel, team: list[LawPersonnel]
) -> str:

    lawyer_details = lawyer.extract_data()
    team_details = json.dumps([member.extract_data() for member in team], indent=2)
    response_schema = get_response_schema(TaskGenerationResponse)

    return f"""
        You are an expert legal case manager AI. Your task is to generate a
        complete and logical task list for an immigration case.

        **Case Details:**
        - Case Type: {case_type}
        - Primary Lawyer: {lawyer_details}
        - Support Team: {team_details}

        **Your Instructions:**
        1.  **Analyze** the case type, lawyer specialty, and team structure.
        2.  **Deduce** a list of necessary tasks, from case initiation to filing.
        3.  **Assign** tasks logically. The `username` for each task should be
            the `username` of the primary lawyer ({lawyer.username}).
        4.  **Assign** `assignees_to_add` to relevant team members (using their emails)
            based on their `personnel_type` and `specialty`.
            (e.g., 'paralegal' for document tasks, 'lawyer' for review tasks).
        5.  **Strictly** follow the `Task` model format for *each* task generated.
            - `task_id` must be a unique string you generate (e.g., "task_001", "task_002").
            - `case_id` must be "case_pending_generation".
            - `status` must be "To-Do".
            - `deadline` should be a `YYYY-MM-DD` string, calculated based on standard
              legal timelines (e.g., 7 days from now, 30 days from now).
              Today's date is {date.today().isoformat()}.
        6.  **Provide** a clear `ai_reasoning` for your task list.
        7.  **Format** your *entire* response as a single, valid JSON object
            matching this schema:
            {response_schema}
    """


def reorder_tasks_prompt(
    tasks: list[Task],
    case_description: str,
    urgency: UrgencyFactor,
    team_structure: TeamStructure,
) -> str:

    task_list_json = json.dumps([t.model_dump() for t in tasks], indent=2)
    team_json = team_structure.model_dump_json(indent=2)
    response_schema = get_response_schema(TaskReorderResponse)
    original_order_ids = [t.task_id for t in tasks]

    return f"""
        You are an expert legal case manager AI. Your task is to reorder a
        list of tasks based on new information.

        **Case Context:**
        - Case Description: {case_description}
        - Urgency Factor: {urgency}
        - Team Structure & Workload: {team_json}

        **Current Task List (in original order):**
        {task_list_json}

        **Your Instructions:**
        1.  **Analyze** the urgency, case description, and team's workload
            (note their `active_cases` and `speciality`).
        2.  **Reorder** the task list to optimize for efficiency and meet the
            urgency.
            - **'Critical' urgency** means tasks blocking filing must be first.
            - **'High' urgency** means prioritize key milestones.
            - Consider team workload: a member with many `active_cases`
              should not be the bottleneck if possible.
            - Respect dependencies (e.g., "Review" must come after "Draft").
        3.  **Do not** add, delete, or modify any tasks. Only change their order
            in the list.
        4.  **Provide** a clear `ai_reasoning` for the new sequence.
        5.  **Populate** `original_order_ids` with this list: {original_order_ids}
        6.  **Populate** `new_order_ids` with the `task_id`s in their new order.
        7.  **Populate** `reordered_tasks` with the full task objects in their
            new order.
        8.  **Format** your *entire* response as a single, valid JSON object
            matching this schema:
            {response_schema}
    """


def update_deadlines_prompt(
    tasks: list[Task],
    case_description: str,
    urgency: UrgencyFactor,
    constraints: str,
) -> str:

    task_list_json = json.dumps([t.model_dump() for t in tasks], indent=2)
    response_schema = get_response_schema(TaskDeadlineUpdateResponse)

    return f"""
        You are an expert legal case manager AI. Your task is to intelligently
        update task deadlines based on new constraints.
        Today's date is {date.today().isoformat()}.

        **Case Context:**
        - Case Description: {case_description}
        - Urgency Factor: {urgency}
        - New Constraints: "{constraints}"

        **Current Task List:**
        {task_list_json}

        **Your Instructions:**
        1.  **Analyze** the `constraints`, `urgency`, and `case_description`.
            "Smartly understand" the constraints. For example:
            - "RFE deadline July 1st" means the final task must be
              well before July 1st.
            - "Client traveling June 10-20" means tasks requiring client
              input cannot have deadlines in that window.
            - "Lawyer on vacation" means tasks assigned to them must be
              scheduled around it.
        2.  **Update** the `deadline` (in 'YYYY-MM-DD' format) for tasks
            as needed.
        3.  **Do not** modify any other field in the tasks.
        4.  **Populate** the `changes_made` list for *every* task
            you changed, explaining *why* (e.g., "Moved deadline before
            client travel").
        5.  **Provide** an overall `ai_reasoning` for your changes.
        6.  **Populate** `updated_tasks` with the full list of tasks
            (including both changed and unchanged ones).
        7.  **Format** your *entire* response as a single, valid JSON object
            matching this schema:
            {response_schema}
    """
