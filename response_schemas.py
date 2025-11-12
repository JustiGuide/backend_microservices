from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Any, Literal, Optional, Union
from datetime import datetime, timezone
from authorization import DateString, PhoneNumber

class ChatResponse(BaseModel):
    text_response: str = Field(
        ...,
        description="The main textual answer to the user's query. This should be comprehensive, well-formatted, and directly address the user's question.",
    )
    references: dict[str, list[str]] = Field(
        default_factory=dict,
        description="A dictionary where each key is an exact sentence from the text_response, and the value is a list of source URLs that directly support that sentence. Only include sentences directly supported by a source file.",
    )


class ChatRequest(BaseModel):
    username: str
    user_input: str
    assistant_type: str
    file_urls: Optional[list[str]] = None
    screenshot_base64: Optional[str] = None
    page_url: Optional[str] = None
    form_context_json: Optional[str] = None
    rag_config_name: Optional[str] = Field("balanced", description="Name of the RAG config to use: speed, accuracy, balanced, large_scale, development")


class DocumentItem(BaseModel):
    """Defines the structure for a single required document."""

    document_name: str = Field(
        ...,
        description="A small display string to indicate what the document would be.",
    )
    description: str = Field(
        ..., description="A detailed description about the document."
    )
    conditions: list[str] = Field(
        ..., description="A list of conditions for when the document would be needed."
    )
    checks: list[str] = Field(
        ..., description="A list of properties/things to check in the document."
    )


class RequiredDocuments(BaseModel):
    """Defines the structure for the final checklist returned by the AI."""

    document_list: list[DocumentItem] = Field(
        ..., description="The final list of required document objects."
    )


class FileClassification(BaseModel):
    """
    Structures the AI's decision on which checklist item a single file best matches.
    """

    best_match: str = Field(
        description="The single best-matching item from the document checklist. If no good match is found, this should be 'None'."
    )
    confidence_score: float = Field(
        description="A score from 0.0 to 1.0 indicating the confidence of the match."
    )
    reasoning: str = Field(
        description="A brief explanation for why this file matches the chosen item, or why it matches none."
    )

REQUIRED_DOCS_SCHEMA = {
    "type": "object",
    "properties": {
        "document_list": {
            "type": "array",
            "items": {"type": "string"},
            "description": "A final, flat list of all required document names for the application.",
        }
    },
    "required": ["document_list"],
}

FILE_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "best_match": {
            "type": "string",
            "description": "The single best-matching item from the document checklist. If no good match is found, return the string 'None'.",
        },
        "confidence_score": {
            "type": "number",
            "description": "A score from 0.0 to 1.0 indicating the confidence of the match.",
        },
        "reasoning": {
            "type": "string",
            "description": "A brief explanation for why this file matches the chosen item, or why it matches none.",
        },
    },
    "required": ["best_match", "confidence_score", "reasoning"],
}

DOC_VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_valid": {
            "type": "boolean",
            "description": "True if the document passes all quality and authenticity checks.",
        },
        "issues_found": {
            "type": "array",
            "items": {"type": "string"},
            "description": "A list of specific issues found, such as 'Blurry text detected' or 'Possible digital alteration'.",
        },
    },
    "required": ["is_valid", "issues_found"],
}


class DocumentValidation(BaseModel):
    is_valid: bool
    issues_found: list[str] = Field(default=[])


class AutofillResponse(BaseModel):
    success: bool = Field(
        ..., description="Whether the autofill generation was successful"
    )
    message: str = Field(
        ..., description="Human-readable message about the operation status"
    )
    autofill_data: dict[str, Union[str, int, float, bool, list[str]]] = Field(
        default_factory=dict,
        description="Generated autofill data with field names as keys and values as form field values",
    )
    form_name: Optional[str] = Field(
        None, description="The form name that was processed"
    )
    generated_field_count: Optional[int] = Field(
        None, description="Number of fields that were successfully generated"
    )
    errors: Optional[list[str]] = Field(
        default_factory=list,
        description="list of any errors or warnings during generation",
    )


class CallSession:
    def __init__(self, profile_uuid: str, rt_session_id: str, rt_ws_url: str):
        self.profile_uuid = profile_uuid
        self.rt_session_id = rt_session_id
        self.rt_ws_url = rt_ws_url
        self.start_at = datetime.now(timezone.utc)
        self.history: list[tuple[str, str]] = []
        self.temp_blocks: list[dict] = []

    def __repr__(self):
        return f"<CallSession {self.profile_uuid} {self.rt_session_id} at {self.start_at.isoformat()}, {len(self.history)} turns>"


CALL_SESSIONS: dict[str, CallSession] = {}

class FluencyRequest(BaseModel):
    username: str = Field(
        ..., description="Username of the user requesting fluency analysis"
    )
    transcript: str = Field(..., description="Speech transcript to analyze for fluency")
    interaction_type: str = Field(
        "general",
        description="Type of interaction (general, interview, conversation, etc.)",
    )
    context_override: Optional[dict[str, Any]] = Field(
        None, description="Optional context override to use instead of database lookup"
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for tracking"
    )


class FluencyResponse(BaseModel):
    success: bool = Field(
        ..., description="Whether the fluency operation was successful"
    )
    message: str = Field(
        ..., description="Human-readable message about the operation status"
    )
    fluency_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Fluency profile data including scores, history, and recommendations",
    )


class FluencyAnalysisResponse(BaseModel):
    success: bool = Field(
        ..., description="Whether the fluency analysis was successful"
    )
    message: str = Field(
        ..., description="Human-readable message about the analysis status"
    )

    # Scores (1-10 scale)
    overall_score: float = Field(0, description="Overall fluency score (1-10)")
    grammar_score: float = Field(0, description="Grammar accuracy score (1-10)")
    vocabulary_score: float = Field(
        0, description="Vocabulary range and appropriateness score (1-10)"
    )
    pronunciation_score: float = Field(
        0, description="Pronunciation clarity score (1-10)"
    )
    fluency_score: float = Field(0, description="Fluency and coherence score (1-10)")
    comprehensibility_score: float = Field(
        0, description="Overall comprehensibility score (1-10)"
    )

    # Qualitative feedback
    strengths: list[str] = Field(
        default_factory=list, description="list of identified strengths"
    )
    areas_for_improvement: list[str] = Field(
        default_factory=list, description="list of areas that need improvement"
    )
    feedback: str = Field("", description="Detailed feedback and suggestions")
    recommendations: list[str] = Field(
        default_factory=list, description="Personalized practice recommendations"
    )

    # Progress tracking
    session_count: int = Field(
        0, description="Total number of fluency sessions completed"
    )
    improvement_over_time: dict[str, Any] = Field(
        default_factory=dict, description="Improvement metrics and trends"
    )


class CallSessionResponse(BaseModel):
    success: bool = Field(
        ..., description="Whether the session creation was successful"
    )
    message: str = Field(
        ..., description="Human-readable message about the session status"
    )
    session_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Session data including session ID, WebSocket URL, and configuration",
    )


class PracticeQuestionRequest(BaseModel):
    username: str = Field(..., description="Username requesting practice questions")
    difficulty_level: str = Field(
        "intermediate", description="Difficulty level: beginner, intermediate, advanced"
    )
    question_count: int = Field(
        5, description="Number of questions to generate", ge=1, le=20
    )
    focus_areas: Optional[list[str]] = Field(
        None,
        description="Specific areas to focus on (grammar, vocabulary, pronunciation, etc.)",
    )


class PracticeQuestion(BaseModel):
    question: str
    type: str
    difficulty: str
    focus_area: Optional[str] = None


class PracticeQuestionResponse(BaseModel):
    success: bool = Field(..., description="Whether question generation was successful")
    message: str = Field(..., description="Human-readable message about the operation")
    questions: list[PracticeQuestion] = Field(
        default_factory=list,
        description="Generated practice questions with metadata",
    )
    difficulty_level: str = Field(
        "", description="Difficulty level of generated questions"
    )
    personalized_for: str = Field(
        "", description="Username the questions were personalized for"
    )
    areas_targeted: list[str] = Field(
        default_factory=list, description="Areas targeted by the questions"
    )


class LawyerEmails(BaseModel):
    lawyer_email: str = Field(description="The email of the recommended lawyer.")


class GeneratedLawyerRecommendations(BaseModel):
    registered: list[LawyerEmails] = Field(
        default_factory=list,
        description="List of recommended registered lawyers, ordered by suitability.",
    )
    unregistered: list[LawyerEmails] = Field(
        default_factory=list,
        description="List of recommended unregistered lawyers, ordered by suitability.",
    )


class QuizAnalysisRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of the user taking the quiz")
    current_quiz_data: list[dict[str, Any]] = Field(
        ..., description="Current quiz attempt data"
    )
    previous_quiz_data: list[list[dict[str, Any]]] = Field(
        default_factory=list, description="Previous quiz attempts data"
    )
    score: str = Field(..., description="Current quiz score (e.g., '18 out of 25')")


class StudyPlanRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of the user")
    weak_topics: list[str] = Field(
        ..., description="Topics where user performed poorly"
    )
    strong_topics: list[str] = Field(
        ..., description="Topics where user performed well"
    )
    quiz_history: list[dict[str, Any]] = Field(
        ..., description="Historical quiz performance"
    )
    target_score: int = Field(default=25, description="Target score for the quiz")


class ProgressTrackingRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of the user")
    historical_data: list[dict[str, Any]] = Field(
        ..., description="Historical quiz performance data"
    )


class PatternAnalysisRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of the user")
    quiz_attempts: list[dict[str, Any]] = Field(
        ..., description="All quiz attempts for pattern analysis"
    )


class PDFConversionRequest(BaseModel):
    pdf_bytes: Optional[str] = Field(None, description="Base64 encoded PDF bytes")
    file_path: Optional[str] = Field(None, description="Path to PDF file")
    dpi: int = Field(default=300, description="DPI for image conversion")


class SignaturePosition(BaseModel):
    page_number: int = Field(..., description="Page number (1-indexed)")
    offsets: list[float] = Field(
        ..., description="[y_offset, x_offset] factors between 0.0 and 1.0"
    )


class SignaturePlacementRequest(BaseModel):
    pdf_bytes: Optional[str] = Field(None, description="Base64 encoded PDF bytes")
    file_path: Optional[str] = Field(None, description="Path to PDF file")
    proposed_positions: list[SignaturePosition] = Field(
        ..., description="Proposed signature positions to validate"
    )

TaskVisibility = Literal["assigned", "all"]
TaskStatus = Literal["To-Do", "In-Progress", "In-Review", "Done", "Rejected"]
UrgencyFactor = Literal["Low", "Medium", "High", "Critical"]
PersonnelType = Literal["lawyer", "nonlawyer", "paralegal", "lawstudent"]

class Task(BaseModel):
    username: str
    task_id: str
    docs_to_delete: Optional[list[str]] = None
    assignees_to_remove: Optional[list[EmailStr]] = None
    case_id: str
    assignees_to_add: Optional[list[EmailStr]] = None
    task_name: Optional[str] = None
    visibility: Optional[TaskVisibility] = None
    status: Optional[TaskStatus] = None
    deadline: Optional[DateString] = None  # e.g., "YYYY-MM-DD"
    description: Optional[str] = None

    @field_validator("deadline")
    def validate_deadline_format(cls, v):
        if v is None:
            return v
        try:
            # Validate if it's a valid ISO date
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("Deadline must be in YYYY-MM-DD format")


class TeamMember(BaseModel):
    name: str
    active_cases: int
    role: Literal["Admin", "Viewer", "Editor"]
    type: PersonnelType
    speciality: Optional[str] = None


class TeamStructure(BaseModel):
    size: int
    members: list[TeamMember]


class TaskGenerationResponse(BaseModel):
    generated_tasks: list[Task]


class TaskReorderResponse(BaseModel):
    reordered_tasks: list[Task]


class DeadlineUpdateChange(BaseModel):
    task_id: str
    task_name: str
    original_deadline: DateString
    new_deadline: DateString = None
    reason: str


class TaskDeadlineUpdateResponse(BaseModel):
    updated_tasks: list[Task]
    changes_made: list[DeadlineUpdateChange]
    ai_reasoning: str = Field(
        ..., description="Explanation from the AI for the deadline changes."
    )


class LawPersonnelSchema(BaseModel):
    email: EmailStr
    username: str
    firstName: str
    lastName: str
    full_legal_name: str
    profile_picture: str
    contact_number: PhoneNumber
    date_of_birth: str
    professional_address: str
    personnel_type: str
    verified: bool
    subscription_tier: str
    receive_emails: bool
    authorize_verification: bool
    consent_data_collection: bool
    law_firm_name: str
    experience: str
    specialty: str
    details: dict
