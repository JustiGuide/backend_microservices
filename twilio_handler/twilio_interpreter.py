import os
from typing import Literal
from dotenv import load_dotenv
from openai import OpenAI
from .twilio_prompts import twilio_contextPrompt, twilio_reasonPrompt

load_dotenv()


class TwilioInterpreter:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def twilio_conversation(
        self, conversation: str, comm_type: str = Literal["call", "text", "whatsapp"]
    ) -> str:
        system_prompt = twilio_reasonPrompt(comm_type)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation},
        ]

        summary_response = self.openai_client.chat.completions.create(
            model="gpt-5",
            messages=messages,
            reasoning_effort="high",
        )

        summary = summary_response.choices[0].message.content
        return summary

    def twilio_updateContext(
        self,
        current_thread: str,
        previous_context: str = None,
        user: str = Literal["USER", "HELPER"],
    ):
        instructions = twilio_contextPrompt(user)
        prev_sum = "None"
        if previous_context:
            prev_sum = f"{user}_CONVERSATION: {previous_context}"
        prompt = f"Previous Summary: {prev_sum}. NEW_{user}_MESSAGE: {current_thread}."

        response = self.openai_client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            reasoning_effort="high",
        )
        return response.choices[0].message.content
