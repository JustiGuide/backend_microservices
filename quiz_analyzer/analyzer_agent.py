import json
from typing import Any


class QuizResultAnalyzerApplication:

    def _categorize_question_by_topic(self, question: str) -> str:
        """Categorize a question into one of the main topic areas"""
        question_lower = question.lower()

        for topic, keywords in self.quiz_topics.items():
            if any(keyword in question_lower for keyword in keywords):
                return topic

        return "general"

    def _analyze_quiz_data(self, quiz_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze individual quiz attempt data"""
        correct_count = 0
        incorrect_questions = []
        correct_questions = []
        topic_performance = {
            "american_government": [],
            "american_history": [],
            "integrated_civics": [],
            "general": [],
        }

        for i, question_data in enumerate(quiz_data, 1):
            question_key = f"question_{i}"
            answer_key = f"answer_{i}"
            submitted_key = f"submitted_answer_{i}"

            if all(
                key in question_data
                for key in [question_key, answer_key, submitted_key]
            ):
                question = question_data[question_key]
                correct_answer = question_data[answer_key]
                submitted_answer = question_data[submitted_key]

                topic = self._categorize_question_by_topic(question)

                if submitted_answer and correct_answer:
                    is_correct = (
                        submitted_answer.lower().strip()
                        == correct_answer.lower().strip()
                    )

                    if is_correct:
                        correct_count += 1
                        correct_questions.append(
                            {
                                "question": question,
                                "topic": topic,
                                "answer": correct_answer,
                            }
                        )
                        topic_performance[topic].append(True)
                    else:
                        incorrect_questions.append(
                            {
                                "question": question,
                                "correct_answer": correct_answer,
                                "submitted_answer": submitted_answer,
                                "topic": topic,
                            }
                        )
                        topic_performance[topic].append(False)

        return {
            "total_questions": len(quiz_data),
            "correct_count": correct_count,
            "incorrect_count": len(quiz_data) - correct_count,
            "accuracy_percentage": (
                (correct_count / len(quiz_data)) * 100 if quiz_data else 0
            ),
            "correct_questions": correct_questions,
            "incorrect_questions": incorrect_questions,
            "topic_performance": topic_performance,
            "passed": correct_count >= self.PASSING_SCORE,
        }

    def _generate_comprehensive_analysis(
        self,
        current_quiz_data: list[dict[str, Any]],
        previous_quiz_data: list[list[dict[str, Any]]],
        score: str,
        email: str,
    ) -> str:
        """Generate comprehensive AI-powered quiz analysis"""
        try:
            # Analyze current attempt
            current_analysis = self._analyze_quiz_data(current_quiz_data)

            # Analyze previous attempts
            previous_analyses = [
                self._analyze_quiz_data(quiz) for quiz in previous_quiz_data
            ]

            # Generate AI analysis
            analysis_prompt = f"""
            You are an expert N-400 naturalization test tutor. Analyze this student's quiz performance and provide detailed feedback.

            CURRENT ATTEMPT RESULTS:
            Score: {score}
            Accuracy: {current_analysis['accuracy_percentage']:.1f}%
            Correct Answers: {current_analysis['correct_count']}/{current_analysis['total_questions']}
            Pass Status: {"PASSED" if current_analysis['passed'] else "NEEDS IMPROVEMENT"}

            CURRENT ATTEMPT DETAILS:
            Incorrect Questions:
            {json.dumps(current_analysis['incorrect_questions'], indent=2)}

            Topic Performance (Current):
            {self._format_topic_performance(current_analysis['topic_performance'])}

            HISTORICAL PERFORMANCE:
            {json.dumps([{
                'attempt': i+1, 
                'accuracy': analysis['accuracy_percentage'], 
                'correct': analysis['correct_count'],
                'topic_performance': self._format_topic_performance(analysis['topic_performance'])
            } for i, analysis in enumerate(previous_analyses)], indent=2)}

            Please provide a comprehensive analysis that includes:

            1. **Overall Performance Assessment**
               - Current performance vs. passing threshold (18/25 correct)
               - Improvement from previous attempts
               - Strengths and weaknesses identification

            2. **Topic-Specific Analysis**
               - American Government (civics and government structure)
               - American History (colonial period, founding, major events)
               - Integrated Civics (geography, symbols, holidays)
               - Which topics need the most attention

            3. **Pattern Recognition**
               - Questions consistently answered incorrectly
               - Areas of improvement since previous attempts
               - Recurring mistake patterns

            4. **Specific Study Recommendations**
               - Priority topics for focused study
               - Specific concepts that need reinforcement
               - Study strategies based on question types missed

            5. **Actionable Next Steps**
               - Immediate study priorities
               - Timeline for improvement
               - Confidence-building strategies

            Keep the tone encouraging but honest about areas needing improvement. Provide specific, actionable advice.
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=2000,
                temperature=0.7,
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error generating analysis: {str(e)}"

    def _format_topic_performance(
        self, topic_performance: dict[str, list[bool]]
    ) -> str:
        """Format topic performance for display"""
        formatted = {}
        for topic, results in topic_performance.items():
            if results:
                correct = sum(results)
                total = len(results)
                percentage = (correct / total) * 100
                formatted[topic] = f"{correct}/{total} ({percentage:.1f}%)"
            else:
                formatted[topic] = "No questions"
        return json.dumps(formatted, indent=2)

    def _create_personalized_study_plan(
        self,
        weak_topics: list[str],
        strong_topics: list[str],
        quiz_history: list[dict[str, Any]],
        target_score: int,
    ) -> str:
        """Create personalized study plan based on performance analysis"""
        try:
            study_plan_prompt = f"""
            Create a personalized study plan for N-400 naturalization test preparation.

            PERFORMANCE ANALYSIS:
            Weak Topics: {weak_topics}
            Strong Topics: {strong_topics}
            Target Score: {target_score}/25
            Quiz History: {json.dumps(quiz_history, indent=2)}

            Create a structured study plan that includes:

            1. **Priority Study Areas** (in order of importance)
               - Most critical weak topics first
               - Specific concepts within each topic

            2. **Weekly Study Schedule**
               - Daily study recommendations
               - Time allocation per topic
               - Progressive difficulty increase

            3. **Study Resources and Methods**
               - Recommended study materials for each topic
               - Practice strategies
               - Memory techniques for difficult concepts

            4. **Practice Schedule**
               - When to take practice quizzes
               - Focus areas for each practice session
               - Progress milestones

            5. **Review Strategy**
               - How to reinforce strong areas
               - Intensive review for weak areas
               - Spaced repetition schedule

            Make the plan practical and achievable, with clear timelines and measurable goals.
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": study_plan_prompt}],
                max_tokens=1500,
                temperature=0.7,
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error creating study plan: {str(e)}"

    def _analyze_learning_progress(
        self, historical_data: list[dict[str, Any]], email: str
    ) -> dict[str, Any]:
        """Analyze learning progress across multiple attempts"""
        try:
            if not historical_data:
                return {"message": "No historical data available for progress analysis"}

            # Calculate progress metrics
            scores = [data.get("score", 0) for data in historical_data]
            accuracy_rates = [data.get("accuracy", 0) for data in historical_data]

            progress_analysis = {
                "total_attempts": len(historical_data),
                "score_trend": {
                    "first_score": scores[0] if scores else 0,
                    "latest_score": scores[-1] if scores else 0,
                    "improvement": scores[-1] - scores[0] if len(scores) > 1 else 0,
                    "best_score": max(scores) if scores else 0,
                    "average_score": sum(scores) / len(scores) if scores else 0,
                },
                "accuracy_trend": {
                    "first_accuracy": accuracy_rates[0] if accuracy_rates else 0,
                    "latest_accuracy": accuracy_rates[-1] if accuracy_rates else 0,
                    "improvement": (
                        accuracy_rates[-1] - accuracy_rates[0]
                        if len(accuracy_rates) > 1
                        else 0
                    ),
                    "best_accuracy": max(accuracy_rates) if accuracy_rates else 0,
                    "average_accuracy": (
                        sum(accuracy_rates) / len(accuracy_rates)
                        if accuracy_rates
                        else 0
                    ),
                },
                "consistency": {
                    "score_variance": self._calculate_variance(scores),
                    "improving_trend": len(scores) > 1 and scores[-1] > scores[0],
                    "ready_for_test": (
                        scores[-1] >= self.PASSING_SCORE if scores else False
                    ),
                },
            }

            return progress_analysis

        except Exception as e:
            return {"error": f"Progress analysis failed: {str(e)}"}

    def _identify_performance_patterns(
        self, quiz_attempts: list[dict[str, Any]], email: str
    ) -> dict[str, Any]:
        """Identify patterns in quiz performance"""
        try:
            patterns = {
                "topic_consistency": {},
                "difficulty_patterns": {},
                "time_patterns": {},
                "improvement_areas": [],
                "persistent_challenges": [],
            }

            # Analyze topic-wise performance patterns
            topic_scores = {
                "american_government": [],
                "american_history": [],
                "integrated_civics": [],
                "general": [],
            }

            for attempt in quiz_attempts:
                quiz_data = attempt.get("quiz_data", [])
                analysis = self._analyze_quiz_data(quiz_data)

                for topic, results in analysis["topic_performance"].items():
                    if results:
                        accuracy = (sum(results) / len(results)) * 100
                        topic_scores[topic].append(accuracy)

            # Calculate topic consistency
            for topic, scores in topic_scores.items():
                if scores:
                    patterns["topic_consistency"][topic] = {
                        "average_accuracy": sum(scores) / len(scores),
                        "consistency_score": 100 - self._calculate_variance(scores),
                        "trend": (
                            "improving"
                            if len(scores) > 1 and scores[-1] > scores[0]
                            else "stable"
                        ),
                    }

            return patterns

        except Exception as e:
            return {"error": f"Pattern identification failed: {str(e)}"}

    def _calculate_variance(self, values: list[float]) -> float:
        """Calculate variance for consistency analysis"""
        if len(values) < 2:
            return 0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance**0.5  # Return standard deviation
