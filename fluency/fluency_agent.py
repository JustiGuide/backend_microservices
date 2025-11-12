import asyncio
import base64
import json
import os
from typing import Any
import httpx
from openai import OpenAI, AsyncOpenAI
from pydantic import EmailStr
from database import Functions
from rag_gateway import RAGGateway
from response_schemas import CallSessionResponse, FluencyAnalysisResponse, FluencyResponse, PracticeQuestion

db_func = Functions()


class FluencyHelper:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    async_openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    assistant_id = os.getenv("N400_ASSISTANT_ID")
    realtime_model = "gpt-realtime"
    realtime_voice = "echo"
    fluency_system_prompt = """
        You are an expert English fluency assessor and coach for immigrants preparing for U.S. citizenship interviews.
        Your role is to:
        1. Analyze spoken English fluency based on grammar, vocabulary, pronunciation, and discourse
        2. Provide constructive feedback for improvement
        Assessment criteria:
        - Grammar accuracy (1-10)
        - Vocabulary range and appropriateness (1-10) 
        - Pronunciation clarity (1-10)
        - Fluency and coherence (1-10)
        - Overall comprehensibility (1-10)
    """

    realtime_system_prompt = """
        You are an examiner whose ONLY task is to test spoken English fluency
        (grammar accuracy, lexical range, coherence, pronunciation). You do NOT ask
        US civics, maths, dates, or factual-knowledge questions.
        • Ask ONE IELTS/TOEFL-style question at a time.
        • Assume the user is speaking English unless their speech is CLEARLY not in English.
        • The user will begin by stating whether they are ready or not.
        • Wait for the user to indicate they are ready before proceeding with questions.
    """

    def __init__(self, rag_config_name: str = "balanced"):
        self.rag_app = RAGGateway(config_name=rag_config_name)

    def _get_immigrant_fluency_context(
        self, immigrant_email: str, context_override: dict[str, Any] = None
    ) -> dict[str, Any]:
        if context_override:
            return context_override

        immigrant = db_func.get_immigrant(immigrant_email)
        profile = db_func.retrieve_fluency_profile(immigrant_email=immigrant.email)
        history = profile.interaction_history or []
        recent_scores = [item.get("overall_score", 0) for item in history[-10:] if "overall_score" in item]
        areas_to_practice = set()
        for item in history[-5:]:
            areas = item.get("areas_for_improvement", [])
            if isinstance(areas, list):
                areas_to_practice.update(areas)
        return {
            "username": immigrant.username,
            "email": immigrant.email,
            "full_legal_name": immigrant.full_legal_name,
            "profile_uuid": str(profile.uuid),
            "last_session_date": (
                profile.last_session_date.isoformat()
                if profile.last_session_date
                else None
            ),
            "interaction_count": len(history),
            "recent_scores": recent_scores,
            "average_recent_score": (
                sum(recent_scores) / len(recent_scores) if recent_scores else 0
            ),
            "current_strengths": profile.strengths or [],
            "areas_for_improvement": profile.areas_for_improvement or [],
            "overall_fluency_score": profile.overall_fluency_score,
        }

    def analyze(
        self,
        immigrant_email: EmailStr,
        transcript: str,
        interaction_type: str = "general",
        interaction_record: dict = {},
        context_override: dict[str, Any] = None,
    ) -> FluencyAnalysisResponse:

        try:
            user_context = self._get_immigrant_fluency_context(
                immigrant_email, context_override
            )

            analysis_result = self._analyze_transcript(
                transcript=transcript,
                user_context=user_context,
                interaction_type=interaction_type,
            )
            db_func.update_fluency_profile(immigrant_email, interaction_record=interaction_record, strengths=analysis_result.get("strengths"), areas_for_improvement=analysis_result.get("areas_for_improvement"), overall_fluency_score=analysis_result.get("overall_score"))

            recommendations = self._generate_recommendations(
                analysis_result
            )

            return FluencyAnalysisResponse(
                success=True,
                message="Fluency analysis completed successfully.",
                overall_score=analysis_result.get("overall_score", 0),
                grammar_score=analysis_result.get("grammar_score", 0),
                vocabulary_score=analysis_result.get("vocabulary_score", 0),
                pronunciation_score=analysis_result.get("pronunciation_score", 0),
                fluency_score=analysis_result.get("fluency_score", 0),
                comprehensibility_score=analysis_result.get(
                    "comprehensibility_score", 0
                ),
                strengths=analysis_result.get("strengths", []),
                areas_for_improvement=analysis_result.get("areas_for_improvement", []),
                feedback=analysis_result.get("feedback", ""),
                recommendations=recommendations,
                session_count=user_context.get("interaction_count", 0),
                improvement_over_time=self._calculate_improvement(
                    immigrant_email, analysis_result.get("overall_score", 0)
                ),
            )

        except Exception as e:
            return FluencyAnalysisResponse(
                success=False,
                message="Sorry, a critical error occurred while analyzing fluency.",
                overall_score=0,
            )

    def get_fluency_profile(self, immigrant_email: EmailStr) -> FluencyResponse:
        try:
            profile = db_func.retrieve_fluency_profile(immigrant_email=immigrant_email)
            if not profile:
                return FluencyResponse(
                    success=False,
                    message="Could not retrieve or create fluency profile for user.",
                    fluency_data={},
                )

            immigrant_context = self._get_immigrant_fluency_context(immigrant_email)
            progress_metrics = self._calculate_progress_metrics(
                profile.interaction_history or []
            )

            fluency_data = {
                "profile_uuid": str(profile.uuid),
                "immigrant_email": profile.immigrant_email,
                "last_session_date": (
                    profile.last_session_date.isoformat()
                    if profile.last_session_date
                    else None
                ),
                "overall_fluency_score": profile.overall_fluency_score,
                "interaction_count": len(profile.interaction_history or []),
                "strengths": profile.strengths or [],
                "areas_for_improvement": profile.areas_for_improvement or [],
                "recent_scores": progress_metrics.get("recent_scores", []),
                "score_trend": progress_metrics.get("trend", "stable"),
                "practice_recommendations": self._generate_practice_recommendations(
                    immigrant_context, profile
                ),
            }

            return FluencyResponse(
                success=True,
                message="Fluency profile retrieved successfully.",
                fluency_data=fluency_data,
            )
        except Exception as e:
            return FluencyResponse(success=False, message=str(e), fluency_data={})

    async def create_realtime_session(self) -> CallSessionResponse:
        try:
            async with httpx.AsyncClient(timeout=20) as http:
                resp = await http.post(
                    "https://api.openai.com/v1/realtime/sessions",
                    headers={
                        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.realtime_model,
                        "voice": self.realtime_voice,
                        "modalities": ["audio", "text"],
                        "instructions": self.realtime_system_prompt
                    },
                )
                resp.raise_for_status()
                data: dict = resp.json()

            ws_url = (
                data.get("url")
                or data.get("ws_url")
                or (data.get("urls") or {}).get("audio")
                or f"wss://api.openai.com/v1/realtime?model={self.realtime_model}"
            )

            session_data = {
                "session_id": data.get("id"),
                "ws_url": ws_url,
                "model": self.realtime_model,
                "voice": self.realtime_voice,
            }

            return CallSessionResponse(
                success=True,
                message="Real-time session created successfully.",
                session_data=session_data,
            )
        except Exception as e:
            return CallSessionResponse(success=False, message=str(e), session_data={})

    async def generate_practice_questions(
        self, immigrant_email: EmailStr, difficulty_level: str = "intermediate"
    ) -> dict[str, Any]:
        """Generate personalized practice questions (from Generated)."""
        try:
            user_context = self._get_immigrant_fluency_context(immigrant_email)

            if self.assistant_id:
                questions = await self._generate_questions_with_assistant(
                    difficulty_level, user_context
                )
            else:
                questions = await self._generate_questions_with_chat(
                    difficulty_level, user_context
                )

            return {
                "success": True,
                "questions": questions,
                "difficulty_level": difficulty_level,
                "personalized_for": immigrant_email,
                "areas_targeted": user_context.get("areas_for_improvement", [])[:3],
            }
        except Exception as e:
            return {"success": False, "error": str(e), "questions": []}

    def _analyze_transcript(
        self, transcript: str, user_context: dict[str, Any], interaction_type: str
    ) -> dict[str, Any]:
        """Analyze transcript using LLM (from Generated)."""
        try:
            system_prompt = self._create_fluency_analysis_prompt(
                user_context, interaction_type
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Please analyze this transcript for English fluency:\n\n{transcript}",
                },
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-5",
                messages=messages,
                response_format={"type": "json_object"},
            )

            analysis_result = json.loads(response.choices[0].message.content)

            return analysis_result
        except Exception as e:
            return {"error": "Analysis failed", "overall_score": 0}

    def _create_fluency_analysis_prompt(
        self, user_context: dict[str, Any], interaction_type: str
    ) -> str:
        """Create system prompt for fluency analysis (from Generated)."""
        return f"""You are an expert English fluency assessor for U.S. citizenship interview preparation.

        **User Context:**
        - Current fluency level: {user_context.get('overall_fluency_score', 'Not assessed')}/10
        - Session count: {user_context.get('interaction_count', 0)}
        - Recent average score: {user_context.get('average_recent_score', 0):.1f}/10
        - Known strengths: {', '.join(user_context.get('current_strengths', ['N/A']))}
        - Areas to improve: {', '.join(user_context.get('areas_for_improvement', ['N/A']))}
        - Interaction type: {interaction_type}

        **Your Task:**
        Analyze the provided English transcript. Provide constructive, encouraging feedback.

        **Assessment Criteria (each scored 1-10):**
        1. Grammar accuracy
        2. Vocabulary range
        3. Pronunciation clarity (based on transcript, infer issues if possible, e.g., homophones)
        4. Fluency and coherence
        5. Overall comprehensibility

        **Response Format (JSON):**
        {{
            "overall_score": <average of all scores, 1-10>,
            "grammar_score": <1-10>,
            "vocabulary_score": <1-10>, 
            "pronunciation_score": <1-10>,
            "fluency_score": <1-10>,
            "comprehensibility_score": <1-10>,
            "strengths": [<list of 2-3 specific positive observations>],
            "areas_for_improvement": [<list of 1-3 specific, actionable improvement areas>],
            "feedback": "<encouraging 2-3 sentence summary with specific examples and suggestions>"
        }}
        """

    def _generate_recommendations(
        self,
        analysis_result: dict[str, Any]
    ) -> list[str]:
        """Generate personalized practice recommendations (from Generated)."""
        # This is a simplified version. For a real app, this could be another LLM call.
        recommendations = []
        if analysis_result.get("grammar_score", 10) < 7:
            recommendations.append(
                "Practice grammar exercises, focusing on verb tenses."
            )
        if analysis_result.get("vocabulary_score", 10) < 7:
            recommendations.append(
                "Expand your vocabulary with citizenship-related terms."
            )
        if analysis_result.get("pronunciation_score", 10) < 7:
            recommendations.append("Practice pronunciation. Try reading texts aloud.")
        if not recommendations:
            recommendations.append("Keep up the great work! Continue practicing daily.")
        return recommendations[:3]  # Max 3 recommendations

    def _calculate_improvement(
        self, immigrant_email: EmailStr, current_score: float
    ) -> dict[str, Any]:
        try:
            profile = db_func.retrieve_fluency_profile(immigrant_email=immigrant_email)
            if not profile or not profile.interaction_history:
                return {"improvement": 0, "trend": "no_data"}

            history = profile.interaction_history
            scores = [
                item.get("overall_score", 0)
                for item in history
                if "overall_score" in item
            ]

            if len(scores) < 1:  # Not enough data (need current score + 1 historical)
                return {"improvement": 0, "trend": "insufficient_data"}

            first_score = scores[0]
            improvement = current_score - first_score
            trend = "stable"
            if len(scores) >= 2:
                if scores[-1] > scores[-2]:
                    trend = "improving"
                if scores[-1] < scores[-2]:
                    trend = "declining"

            return {
                "improvement": round(improvement, 2),
                "trend": trend,
                "sessions_completed": len(scores),
                "average_score": round(sum(scores) / len(scores), 2),
            }
        except Exception as e:
            return {"improvement": 0, "trend": "error"}

    def _calculate_progress_metrics(
        self, interaction_history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate progress metrics (from Generated)."""
        if not interaction_history:
            return {"recent_scores": [], "trend": "no_data"}
        scores = [
            item.get("overall_score", 0)
            for item in interaction_history
            if "overall_score" in item
        ]
        recent_scores = scores[-10:]
        trend = "stable"
        if len(recent_scores) >= 2:
            if recent_scores[-1] > recent_scores[0]:
                trend = "improving"
            if recent_scores[-1] < recent_scores[0]:
                trend = "declining"
        return {"recent_scores": recent_scores, "trend": trend}

    def _generate_practice_recommendations(
        self, user_context: dict[str, Any]
    ) -> list[str]:
        """Generate practice recommendations (from Generated)."""
        recommendations = []
        overall_score = user_context.get("overall_fluency_score", 0)
        if overall_score < 5:
            recommendations.append("Focus on basic conversation and simple sentences.")
        elif overall_score < 8:
            recommendations.append(
                "Work on expanding vocabulary and complex sentences."
            )
        else:
            recommendations.append("Practice advanced topics and nuanced expression.")

        areas = user_context.get("areas_for_improvement", [])
        for area in areas[:2]:
            recommendations.append(f"Targeted practice: {area}")
        return recommendations[:5]

    async def _generate_questions_with_assistant(
        self, difficulty_level: str, user_context: dict[str, Any]
    ) -> list[PracticeQuestion]:
        """Generate questions using OpenAI Assistant (from Generated)."""
        # ... (Implementation from generated code) ...
        return await self._generate_questions_with_chat(
            difficulty_level, user_context
        )

    async def _generate_questions_with_chat(
        self, difficulty_level: str, user_context: dict[str, Any]
    ) -> list[PracticeQuestion]:
        try:
            prompt = f"""
            Generate 5 English fluency practice questions for citizenship interview preparation.
            Difficulty level: {difficulty_level}
            User's current fluency score: {user_context.get('overall_fluency_score', 0)}/10
            Areas to improve: {', '.join(user_context.get('areas_for_improvement', []))}
            
            Return a JSON array of objects with keys: "question", "type", "difficulty", "focus_area".
            Example: [{{"question": "...", "type": "personal", "difficulty": "intermediate", "focus_area": "grammar"}}]
            """
            response = await self.async_openai_client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an English fluency coach generating practice questions.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            # The response content is a JSON string, parse it
            content = json.loads(response.choices[0].message.content)
            # The prompt asks for an array, which might be nested in a key
            if isinstance(content, list):
                questions_data = content
            elif isinstance(content, dict) and "questions" in content:
                questions_data = content["questions"]
            else:  # Fallback if structure is unexpected
                questions_data = [content]

            # Validate and cast to PracticeQuestion models
            valid_questions = []
            for q_data in questions_data:
                if isinstance(q_data, dict) and "question" in q_data:
                    valid_questions.append(PracticeQuestion(**q_data))

            return valid_questions

        except Exception as e:
            return [
                PracticeQuestion(
                    question="Tell me about yourself.",
                    type="personal",
                    difficulty="intermediate",
                    focus_area="fluency",
                )
            ]

    # --- Methods from Legacy FluencyAgent (Merged) ---

    async def _send_session_update(self, ws):
        """Sends the session update message to OpenAI WS (from Legacy)."""
        await ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "turn_detection": {"type": "server_vad"},
                        "voice": self.realtime_voice,
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "instructions": self.realtime_system_prompt,
                        "modalities": ["text", "audio"],
                        "temperature": 0.8,
                        "input_audio_transcription": {"model": "gpt-4o-transcribe"},
                    },
                }
            )
        )

    async def tts_wav(self, text: str) -> str:
        """Converts text to speech and returns base64 (from Legacy)."""
        async with httpx.AsyncClient(timeout=30) as cli:
            res = await cli.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini-tts",  # Faster model for TTS
                    "voice": self.realtime_voice,
                    "input": text,
                    "response_format": "wav",  # Use wav for compatibility
                },
            )
            res.raise_for_status()
        wav_bytes = res.content
        return base64.b64encode(wav_bytes).decode("ascii")
