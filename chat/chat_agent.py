import os
from typing import Optional
from openai import OpenAI
from openai.types.chat import ChatCompletion
from dotenv import load_dotenv
from .chat_prompts import AgentPrompts
from rag_gateway import RAGGateway
from response_schemas import ChatResponse
from .chat_agent_governance import Governance
import json

load_dotenv()


class Chat:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompts = AgentPrompts()

    def __init__(self, rag_config_name: str = "balanced"):
        self.rag_app = RAGGateway(config_name=rag_config_name)
        self.assistant_handlers = {
            "relo": self._handle_simple_relocation,
            "dolores": self._handle_nuanced_immigrant,
            "form": self._handle_form_specific,
            "help": self._handle_site_helper,
            "lawyer": self._handle_lawyer_immigrant,
            "n400": self._handle_n400_helper,
        }

    def assistant(
        self,
        username: str,
        user_input: str,
        assistant_type: str,
        file_urls: Optional[list[str]] = None,
        **kwargs,
    ) -> ChatResponse:
        """
        Dispatches the user request to the appropriate assistant handler.
        This is the single entry point for all chat interactions.
        """
        print(
            f"CHAT DISPATCH: New request for '{username}', assistant: '{assistant_type}'"
        )

        handler = self.assistant_handlers.get(assistant_type)
        if not handler:
            print(
                f"CHAT DISPATCH: No handler found for assistant type '{assistant_type}'"
            )
            return ChatResponse(
                text_response=f"Error: Assistant type '{assistant_type}' is not supported.",
                references={},
            )

        try:
            return handler(username, user_input, file_urls=file_urls, **kwargs)
        except Exception as e:
            print(
                f"CHAT HANDLER Error: Exception in '{assistant_type}' handler for '{username}': {e}",
                exc_info=True,
            )
            return ChatResponse(
                text_response="Sorry, a critical error occurred while processing your request.",
                references={},
            )

    def _get_llm_response(
        self, system_prompt: str, user_input: str, visual_context: Optional[str] = None
    ) -> ChatCompletion:
        messages = [{"role": "system", "content": system_prompt}]
        user_content = [{"type": "text", "text": user_input}]

        if visual_context:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{visual_context}"},
                }
            )

        messages.append({"role": "user", "content": user_content})

        return self.openai_client.chat.completions.create(
            model="gpt-5",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )

    def _parse_and_log_response(
        self,
        response: ChatCompletion,
        user_input: str,
        assistant_type: str,
    ) -> ChatResponse:
        response_content = response.choices[0].message.content
        parsed_json = json.loads(response_content)
        chat_response = ChatResponse(**parsed_json)
        Governance.ai_chat_information(user_input, response, assistant_type)
        return chat_response

    def _handle_simple_relocation(
        self,
        username: str,
        user_input: str,
        file_urls: Optional[list[str]] = None,
        **kwargs,
    ) -> ChatResponse:
        context = self.rag_app.retrieve_hybrid_context(
            username=username,
            query=user_input,
            file_urls=file_urls,
            top_k_files=5,
            top_k_general=2,
        )
        system_prompt = self.prompts.get_system_prompt("relo", context)
        response = self._get_llm_response(system_prompt, user_input)
        return self._parse_and_log_response(response, username, user_input, "relo")

    def _handle_nuanced_immigrant(
        self,
        username: str,
        user_input: str,
        file_urls: Optional[list[str]] = None,
        **kwargs,
    ) -> ChatResponse:
        context = self.rag_app.retrieve_hybrid_context(
            username=username,
            query=user_input,
            file_urls=file_urls,
            top_k_files=7,
            top_k_general=4,
        )
        system_prompt = self.prompts.get_system_prompt("dolores", context)
        response = self._get_llm_response(system_prompt, user_input)
        return self._parse_and_log_response(response, username, user_input, "dolores")

    def _handle_form_specific(
        self,
        username: str,
        user_input: str,
        file_urls: Optional[list[str]] = None,
        **kwargs,
    ) -> ChatResponse:
        form_context_json = kwargs.get("form_context_json", "{}")
        context = self.rag_app.retrieve_hybrid_context(
            username=username,
            query=user_input,
            file_urls=file_urls,
            top_k_files=6,
            top_k_general=3,
        )
        system_prompt = self.prompts.get_system_prompt(
            "form", context, form_context_json=form_context_json
        )
        response = self._get_llm_response(system_prompt, user_input)
        return self._parse_and_log_response(response, username, user_input, "form")

    def _handle_site_helper(
        self,
        username: str,
        user_input: str,
        file_urls: Optional[list[str]] = None,
        **kwargs,
    ) -> ChatResponse:
        db_context = kwargs.get("site_context")
        screenshot_base64 = kwargs.get("screenshot_base64")

        system_prompt = self.prompts.get_system_prompt(
            "help", db_context, page_url=kwargs.get("page_url")
        )
        response = self._get_llm_response(
            system_prompt, user_input, visual_context=screenshot_base64
        )
        return self._parse_and_log_response(response, username, user_input, "help")

    def _handle_lawyer_immigrant(
        self,
        username: str,
        user_input: str,
        file_urls: Optional[list[str]] = None,
        **kwargs,
    ) -> ChatResponse:
        context = self.rag_app.retrieve_hybrid_context(
            username=username,
            query=user_input,
            file_urls=file_urls,
            top_k_files=10,
            top_k_general=5,
        )
        system_prompt = self.prompts.get_system_prompt("lawyer", context)
        response = self._get_llm_response(system_prompt, user_input)
        return self._parse_and_log_response(response, username, user_input, "lawyer")

    def _handle_n400_helper(
        self,
        username: str,
        user_input: str,
        file_urls: Optional[list[str]] = None,
        **kwargs,
    ) -> ChatResponse:
        context = self.rag_app.retrieve_hybrid_context(
            username=username,
            query=user_input,
            file_urls=file_urls,
            top_k_files=5,
            top_k_general=3,
        )
        system_prompt = self.prompts.get_system_prompt("n400", context)
        response = self._get_llm_response(system_prompt, user_input)
        return self._parse_and_log_response(response, username, user_input, "n400")
