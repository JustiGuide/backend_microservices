import json
import os
from dotenv import load_dotenv
from fastapi import HTTPException
from openai import OpenAI
from pydantic import BaseModel
from response_schemas import Task, TeamStructure, UrgencyFactor, TaskDeadlineUpdateResponse, TaskGenerationResponse, TaskReorderResponse
from database import LawPersonnel
from .task_generator_prompts import generate_tasks_prompt, reorder_tasks_prompt, update_deadlines_prompt


load_dotenv()

class TaskManagementAgent:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def _get_response(
        client: OpenAI, prompt: str, response_model: BaseModel, model: str = "gpt-5"
    ) -> BaseModel:
        """
        Calls the OpenAI API in JSON mode and parses the response
        into the specified Pydantic model.
        """
        try:
            response = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that only responds in valid JSON, adhering to the user's provided schema.",
                    },
                    {"role": "user", "content": prompt},
                ],
                reasoning_effort="high"
            )

            response_content = response.choices[0].message.content
            parsed_response = response_model.model_validate_json(response_content)

            return parsed_response

        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail="AI returned invalid JSON.")
        except Exception as e:
            raise

    async def generate_task_list(
        self,
        case_type: str,
        lawyer: LawPersonnel,
        team: list[LawPersonnel],
    ) -> TaskGenerationResponse:
        """
        Generates a new task list for a case.
        """
        try:
            prompt = generate_tasks_prompt(case_type, lawyer, team)

            ai_response = await self._get_response(
                client=self.openai_client,
                prompt=prompt,
                response_model=TaskGenerationResponse,
            )

            return ai_response

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"AI Task Generation Failed: {str(e)}"
            )

    async def reorder_task_list(
        self,
        tasks: list[Task],
        case_description: str,
        urgency: UrgencyFactor,
        team_structure: TeamStructure,
    ) -> TaskReorderResponse:
        """
        Reorders an existing task list based on new parameters.
        """
        try:
            prompt = reorder_tasks_prompt(
                tasks, case_description, urgency, team_structure
            )

            ai_response = await self._get_response(
                client=self.openai_client,
                prompt=prompt,
                response_model=TaskReorderResponse,
            )

            return ai_response

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"AI Task Reordering Failed: {str(e)}"
            )

    async def update_task_deadlines(
        self,
        tasks: list[Task],
        case_description: str,
        urgency: UrgencyFactor,
        constraints: str,
    ) -> TaskDeadlineUpdateResponse:
        """
        Updates deadlines for tasks based on smart analysis of constraints.
        """
        try:
            prompt = update_deadlines_prompt(
                tasks, case_description, urgency, constraints
            )

            ai_response = await self._get_response(
                client=self.openai_client,
                prompt=prompt,
                response_model=TaskDeadlineUpdateResponse,
            )

            return ai_response

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"AI Deadline Update Failed: {str(e)}"
            )
