from typing import Union
import json


def generate_recommendation_prompt(immigrant_data: dict[str, str], retrieved_context: Union[str, None], messages: list[str], registered_lawyers: list[dict[str, str]], unregistered_lawyers: list[dict[str, str]], kyc_data: dict[str, list[str]], tool_name: str) -> str:
    RECOMMENDATION_PROMPT_RAG = f"""
        You are a legal matching assistant. Your task is to analyze the user's situation based *only* on the provided context and data, then **rank all** provided lawyers based **strictly on calculated suitability** by calling the required tool.

        **Immigrant Profile:**
        - Username: {immigrant_data.get('username', 'N/A')}
        - Location: {immigrant_data.get('location', 'N/A')}
        - Email: {immigrant_data.get('email', 'N/A')}

        **Retrieved Context (Primary Source):**
        Analyze this context carefully to understand the user's legal needs, case type, location, and relevant circumstances.
        context
        {retrieved_context if retrieved_context else "No relevant document context was found for the user."}
        Auxiliary Data Sources (Use if relevant and not conflicting with context):

        KYC information (Question: [Answers]): {json.dumps(kyc_data)}
        Recent Message history: {json.dumps(messages[-5:], indent=2)} [Last 5 messages shown]
        Available Lawyers (You MUST rank ALL of these):

        Registered Lawyers: {json.dumps(registered_lawyers, indent=2)}
        Unregistered Lawyers: {json.dumps(unregistered_lawyers, indent=2)}
        Ranking Criteria (Apply to ALL lawyers):
        Evaluate suitability based only on these factors, in this order of importance:

        Location Match: Strong match between lawyer location and user location is highest priority.
        Expertise Relevance: Strong match between lawyer expertise and user's needs (inferred from context/data) is second highest priority.
        Experience: Consider listed experience level if available (higher is better).
        Other Factors: Use other relevant details only if the above are tied.
        Task:

        Determine the user's likely legal needs from the Retrieved Context and Auxiliary Data.
        For every single lawyer in the 'Available Lawyers' lists, calculate a suitability score based strictly on the Ranking Criteria above.
        You MUST call the function tool named '{tool_name}' to provide your results.
        Populate the tool's arguments ('registered' and 'unregistered') with the emails of ALL the lawyers originally provided in the corresponding input lists.
        CRITICAL SORTING INSTRUCTION: The lists of emails you provide in the tool call MUST be sorted STRICTLY from MOST suitable to LEAST suitable based on your calculated suitability scores according to the Ranking Criteria. The lawyer who best matches the criteria (especially location and expertise) must be first. The lawyer who least matches must be last.
        DO NOT sort alphabetically. The final order must reflect suitability ONLY. Verify the list is not alphabetical before outputting unless it coincidentally matches the suitability ranking.
        Include ALL lawyers. Do not omit any.
        Do NOT provide explanations or any text outside the required tool call.
        Output: Call the '{tool_name}' tool with the 'registered' and 'unregistered' lists containing ALL original emails, sorted ONLY by calculated suitability (most suitable first).
        """
    return RECOMMENDATION_PROMPT_RAG.strip()
