from fastapi import APIRouter, HTTPException
from fastapi import Path as endpoint_path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from helpers import Helpers
from database import Functions
from .analyzer_agent import QuizResultAnalyzerApplication


app = APIRouter()
db_func = Functions()
analyzer = QuizResultAnalyzerApplication()

class NaturalizationQuiz(BaseModel):
    immigrant_email: EmailStr
    start: bool = False
    end: bool = False
    answer_selected: str = None
    option_bank: dict[str, str] = None


@app.post("/naturalization_quiz/q{question_number}/")
async def naturalization_quiz(
    payload: NaturalizationQuiz,
    question_number: int = endpoint_path(..., ge=1, le=25),
):
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    if question_number == 1 and payload.start:
        db_func.refresh_n400_quiz(immigrant.email)
    elif question_number > 1 and not payload.start:
        pass
    else:
        return HTTPException(
            status_code=400,
            detail="Quiz already in progress. Please complete the current question before starting a new one.",
        )
    previous_n400_quiz = db_func.retrieve_n400_current(immigrant.email)
    question = Helpers.get_random_n400_question(previous_n400_quiz)
    if question is None:
        return {"message": "No more questions available."}

    db_func.add_n400_question(
        email=immigrant.email,
        index_number=question_number,
        qa_pair=[question["question"], question["options"][question["answer"]]],
    )
    return JSONResponse(
        {
            "question_number": question_number,
            "question": question["question"],
            "options": question["options"],
        }
    )


@app.post("/submit_naturalization_answer/q{question_number}/")
async def submit_naturalization_answer(
    payload: NaturalizationQuiz,
    question_number: int = endpoint_path(..., ge=1, le=25),
):
    immigrant = db_func.get_immigrant(payload.immigrant_email)
    report = None
    score = None
    correct_answer_dict = None
    is_correct = False
    answer_string = payload.option_bank.get(payload.answer_selected, None)
    if payload.answer_selected is not None:
        is_correct, correct_answer = db_func.check_n400_answer(
            email=immigrant.email,
            index_number=question_number,
            submitted_answer=answer_string,
        )
        selected_option = [
            option
            for option in payload.option_bank
            if payload.option_bank[option] == correct_answer
        ]
        if len(selected_option) == 0:
            return HTTPException(
                status_code=400, detail="Correct answer not found in option bank."
            )
        correct_answer_dict = {
            "option": payload.option_bank[selected_option[0]],
            "answer": correct_answer,
        }

    if question_number == 25 or payload.end:
        score, user_quiz_data, old_quiz_data = db_func.retrieve_n400_score(
            immigrant.email
        )
        report = analyzer._generate_comprehensive_analysis(
            user_quiz_data, old_quiz_data, score, immigrant.email
        )
    return {
        "result": is_correct,
        "correct_answer": correct_answer_dict,
        "report": report,
        "score": score,
    }
