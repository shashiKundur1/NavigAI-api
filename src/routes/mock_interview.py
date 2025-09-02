from quart import Blueprint, request, jsonify, send_file
from datetime import datetime
from typing import Dict, Any, Optional
import os
import tempfile
import json
from models.mock_interview import (
    InterviewSession,
    Question,
    Answer,
    QuestionType,
    DifficultyLevel,
    InterviewStatus,
    PerformanceMetrics,
)
from services.mock_interview_service import MockInterviewService
from db.firebase_db import (
    save_interview_session,
    get_interview_session,
    update_interview_session,
    get_all_interview_sessions,
    get_user_sessions,
    get_analytics_data,
    health_check as firebase_health_check,
)

mock_interview_bp = Blueprint("mock_interview", __name__)
service = MockInterviewService()


@mock_interview_bp.route("/sessions", methods=["POST"])
async def create_interview_session():
    """Create a new interview session"""
    try:
        data = await request.get_json()
        # Validate required fields
        required_fields = ["job_title", "job_description", "candidate_id"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Create session
        session = service.create_interview_session(
            job_title=data["job_title"],
            job_description=data["job_description"],
            candidate_id=data["candidate_id"],
        )

        return (
            jsonify(
                {
                    "session_id": session.id,
                    "status": session.status.value,
                    "created_at": session.created_at.isoformat(),
                    "message": "Interview session created successfully",
                }
            ),
            201,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>/start", methods=["POST"])
async def start_interview():
    """Start an interview session"""
    try:
        session_id = session_id
        # Start interview
        success = service.start_interview(session_id)
        if success:
            return jsonify(
                {
                    "session_id": session_id,
                    "status": "started",
                    "message": "Interview started successfully",
                }
            )
        else:
            return jsonify({"error": "Failed to start interview"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>/next-question", methods=["GET"])
async def get_next_question():
    """Get the next question for the interview"""
    try:
        session_id = session_id
        # Get next question
        question = service.get_next_question(session_id)
        if question:
            return jsonify(
                {
                    "question_id": question.id,
                    "text": question.text,
                    "type": question.type.value,
                    "difficulty": question.difficulty.value,
                    "category": question.category,
                    "expected_keywords": question.expected_keywords,
                }
            )
        else:
            return jsonify({"error": "No more questions available"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>/record/start", methods=["POST"])
async def start_recording():
    """Start recording audio for the interview"""
    try:
        session_id = session_id
        # Start recording
        service.start_audio_recording(session_id)
        return jsonify(
            {
                "session_id": session_id,
                "status": "recording",
                "message": "Recording started",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>/record/stop", methods=["POST"])
async def stop_recording():
    """Stop recording and analyze the response"""
    try:
        session_id = session_id
        # Stop recording
        audio_file = service.stop_audio_recording()
        if not audio_file:
            return jsonify({"error": "No audio recorded"}), 400

        # Transcribe audio
        transcribed_text = service.transcribe_audio(audio_file)

        # Get current question
        session_data = get_interview_session(session_id)
        if not session_data:
            return jsonify({"error": "Session not found"}), 404

        session = InterviewSession(**session_data)

        # Get the last asked question
        if not session.questions_asked:
            return jsonify({"error": "No questions asked yet"}), 400

        question_id = session.questions_asked[-1]
        question = next((q for q in service.question_bank if q.id == question_id), None)
        if not question:
            return jsonify({"error": "Question not found"}), 404

        # Analyze response
        answer = service.analyze_response(
            audio_file, transcribed_text, question, session
        )

        # Submit answer
        service.submit_answer(session_id, answer)

        # Clean up audio file
        if os.path.exists(audio_file):
            os.remove(audio_file)

        return jsonify(
            {
                "session_id": session_id,
                "transcribed_text": transcribed_text,
                "analysis": {
                    "technical_score": answer.technical_score,
                    "communication_score": (
                        answer.fluency_score + answer.confidence_score
                    )
                    / 2,
                    "confidence_score": answer.confidence_score,
                    "sentiment_score": answer.sentiment_score,
                    "fluency_score": answer.fluency_score,
                    "emotion_scores": answer.emotion_scores,
                },
                "message": "Response analyzed successfully",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>/should-end", methods=["GET"])
async def should_end_interview():
    """Check if interview should be ended"""
    try:
        session_id = session_id
        # Check if interview should end
        should_end = service.should_end_interview(session_id)
        return jsonify(
            {
                "session_id": session_id,
                "should_end": should_end,
                "reason": (
                    "Maximum questions reached" if should_end else "Continue interview"
                ),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>/end", methods=["POST"])
async def end_interview():
    """End the interview session"""
    try:
        session_id = session_id
        # End interview
        success = service.end_interview(session_id)
        if success:
            return jsonify(
                {
                    "session_id": session_id,
                    "status": "completed",
                    "message": "Interview ended successfully",
                }
            )
        else:
            return jsonify({"error": "Failed to end interview"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>/report", methods=["GET"])
async def generate_report():
    """Generate and download interview report"""
    try:
        session_id = session_id
        # Generate report
        report_path = service.generate_interview_report(session_id)
        if report_path:
            return await send_file(
                report_path,
                as_attachment=True,
                download_name=f"interview_report_{session_id}.pdf",
                mimetype="application/pdf",
            )
        else:
            return jsonify({"error": "Failed to generate report"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>", methods=["GET"])
async def get_session():
    """Get interview session details"""
    try:
        session_id = session_id
        # Get session data
        session_data = get_interview_session(session_id)
        if not session_data:
            return jsonify({"error": "Session not found"}), 404
        return jsonify(session_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>/progress", methods=["GET"])
async def get_session_progress():
    """Get interview session progress"""
    try:
        session_id = session_id
        # Get session data
        session_data = get_interview_session(session_id)
        if not session_data:
            return jsonify({"error": "Session not found"}), 404

        session = InterviewSession(**session_data)

        # Calculate progress
        progress = {
            "session_id": session_id,
            "status": session.status.value,
            "questions_asked": len(session.questions_asked),
            "answers_count": len(session.answers),
            "current_question_index": session.current_question_index,
            "started_at": (
                session.started_at.isoformat() if session.started_at else None
            ),
            "completed_at": (
                session.completed_at.isoformat() if session.completed_at else None
            ),
            "progress_percentage": (len(session.answers) / 20)
            * 100,  # Updated to 20 questions
        }

        # Add performance summary if answers exist
        if session.answers:
            latest_answer = session.answers[-1]
            avg_technical = sum(a.technical_score for a in session.answers) / len(
                session.answers
            )
            progress["performance_summary"] = {
                "latest_technical_score": latest_answer.technical_score,
                "latest_communication_score": (
                    latest_answer.fluency_score + latest_answer.confidence_score
                )
                / 2,
                "latest_confidence_score": latest_answer.confidence_score,
                "average_technical_score": avg_technical,
            }

        return jsonify(progress)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>/text-to-speech", methods=["POST"])
async def text_to_speech():
    """Convert text to speech"""
    try:
        session_id = session_id
        data = await request.get_json()
        if "text" not in data:
            return jsonify({"error": "Missing text field"}), 400

        text = data["text"]

        # Convert text to speech
        success = service.text_to_speech(text)
        if success:
            return jsonify(
                {
                    "session_id": session_id,
                    "text": text,
                    "status": "spoken",
                    "message": "Text converted to speech successfully",
                }
            )
        else:
            return jsonify({"error": "Failed to convert text to speech"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions", methods=["GET"])
async def get_all_sessions():
    """Get all interview sessions (with optional filtering)"""
    try:
        # Get query parameters
        candidate_id = request.args.get("candidate_id")
        status = request.args.get("status")
        limit = int(request.args.get("limit", 50))

        # Get all sessions from Firebase
        all_sessions = get_all_interview_sessions()

        # Filter sessions
        filtered_sessions = []
        for session_data in all_sessions:
            session = InterviewSession(**session_data)

            # Apply filters
            if candidate_id and session.candidate_id != candidate_id:
                continue
            if status and session.status.value != status:
                continue

            # Add to filtered list
            filtered_sessions.append(
                {
                    "session_id": session.id,
                    "job_title": session.job_title,
                    "candidate_id": session.candidate_id,
                    "status": session.status.value,
                    "created_at": session.created_at.isoformat(),
                    "started_at": (
                        session.started_at.isoformat() if session.started_at else None
                    ),
                    "completed_at": (
                        session.completed_at.isoformat()
                        if session.completed_at
                        else None
                    ),
                    "questions_asked": len(session.questions_asked),
                    "answers_count": len(session.answers),
                }
            )

        # Sort by creation date (newest first)
        filtered_sessions.sort(key=lambda x: x["created_at"], reverse=True)

        # Apply limit
        filtered_sessions = filtered_sessions[:limit]

        return jsonify(
            {
                "sessions": filtered_sessions,
                "total": len(filtered_sessions),
                "limit": limit,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/sessions/<session_id>/answers", methods=["GET"])
async def get_session_answers():
    """Get all answers for a session"""
    try:
        session_id = session_id
        # Get session data
        session_data = get_interview_session(session_id)
        if not session_data:
            return jsonify({"error": "Session not found"}), 404

        session = InterviewSession(**session_data)

        # Format answers
        answers = []
        for answer in session.answers:
            # Get question details
            question = next(
                (q for q in service.question_bank if q.id == answer.question_id), None
            )

            answer_data = {
                "question_id": answer.question_id,
                "question_text": question.text if question else "Unknown question",
                "question_type": question.type.value if question else "unknown",
                "question_difficulty": (
                    question.difficulty.value if question else "unknown"
                ),
                "answer_text": answer.text,
                "transcribed_text": answer.transcribed_text,
                "audio_duration": answer.audio_duration,
                "timestamp": answer.timestamp.isoformat(),
                "scores": {
                    "technical": answer.technical_score,
                    "communication": (answer.fluency_score + answer.confidence_score)
                    / 2,
                    "confidence": answer.confidence_score,
                    "sentiment": answer.sentiment_score,
                    "fluency": answer.fluency_score,
                },
                "emotion_scores": answer.emotion_scores,
            }
            answers.append(answer_data)

        return jsonify(
            {
                "session_id": session_id,
                "answers": answers,
                "total_answers": len(answers),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/questions", methods=["GET"])
async def get_question_bank():
    """Get all available questions in the question bank"""
    try:
        # Get query parameters
        question_type = request.args.get("type")
        difficulty = request.args.get("difficulty")
        category = request.args.get("category")

        # Filter questions
        filtered_questions = []
        for question in service.question_bank:
            # Apply filters
            if question_type and question.type.value != question_type:
                continue
            if difficulty and question.difficulty.value != difficulty:
                continue
            if category and question.category != category:
                continue

            # Add to filtered list
            question_data = {
                "id": question.id,
                "text": question.text,
                "type": question.type.value,
                "difficulty": question.difficulty.value,
                "category": question.category,
                "expected_keywords": question.expected_keywords,
            }
            filtered_questions.append(question_data)

        return jsonify(
            {"questions": filtered_questions, "total": len(filtered_questions)}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/analytics/performance", methods=["GET"])
async def get_performance_analytics():
    """Get performance analytics across all sessions"""
    try:
        # Get query parameters
        candidate_id = request.args.get("candidate_id")
        job_title = request.args.get("job_title")
        days = int(request.args.get("days", 30))

        # Get analytics data using our new function
        analytics_data = get_analytics_data(days)

        # Get all sessions for detailed analysis
        all_sessions = get_all_interview_sessions()

        # Filter and process sessions
        performance_data = []
        for session_data in all_sessions:
            session = InterviewSession(**session_data)

            # Apply filters
            if candidate_id and session.candidate_id != candidate_id:
                continue
            if job_title and session.job_title != job_title:
                continue

            # Check if session is completed and has performance metrics
            if (
                session.status == InterviewStatus.COMPLETED
                and session.performance_metrics
            ):
                # Check if session is within the specified date range
                if session.completed_at:
                    days_diff = (datetime.now() - session.completed_at).days
                    if days_diff > days:
                        continue

                metrics = PerformanceMetrics(**session.performance_metrics)
                performance_data.append(
                    {
                        "session_id": session.id,
                        "candidate_id": session.candidate_id,
                        "job_title": session.job_title,
                        "completed_at": (
                            session.completed_at.isoformat()
                            if session.completed_at
                            else None
                        ),
                        "performance_metrics": metrics.dict(),
                        "answers_count": len(session.answers),
                    }
                )

        # Calculate aggregate statistics
        if performance_data:
            avg_technical = sum(
                p["performance_metrics"]["technical_score"] for p in performance_data
            ) / len(performance_data)
            avg_communication = sum(
                p["performance_metrics"]["communication_score"]
                for p in performance_data
            ) / len(performance_data)
            avg_emotional = sum(
                p["performance_metrics"]["emotional_intelligence_score"]
                for p in performance_data
            ) / len(performance_data)
            avg_overall = sum(
                p["performance_metrics"]["overall_score"] for p in performance_data
            ) / len(performance_data)

            # Question type performance
            question_type_performance = {}
            difficulty_performance = {}

            for session_data in all_sessions:
                session = InterviewSession(**session_data)
                if session.status == InterviewStatus.COMPLETED:
                    for answer in session.answers:
                        question = next(
                            (
                                q
                                for q in service.question_bank
                                if q.id == answer.question_id
                            ),
                            None,
                        )
                        if question:
                            # Question type performance
                            q_type = question.type.value
                            if q_type not in question_type_performance:
                                question_type_performance[q_type] = []
                            question_type_performance[q_type].append(
                                answer.technical_score
                            )

                            # Difficulty performance
                            difficulty = question.difficulty.value
                            if difficulty not in difficulty_performance:
                                difficulty_performance[difficulty] = []
                            difficulty_performance[difficulty].append(
                                answer.technical_score
                            )

            # Calculate averages
            for q_type in question_type_performance:
                question_type_performance[q_type] = sum(
                    question_type_performance[q_type]
                ) / len(question_type_performance[q_type])

            for difficulty in difficulty_performance:
                difficulty_performance[difficulty] = sum(
                    difficulty_performance[difficulty]
                ) / len(difficulty_performance[difficulty])
        else:
            avg_technical = avg_communication = avg_emotional = avg_overall = 0
            question_type_performance = {}
            difficulty_performance = {}

        return jsonify(
            {
                "analytics": {
                    "total_sessions": len(performance_data),
                    "average_scores": {
                        "technical": avg_technical,
                        "communication": avg_communication,
                        "emotional_intelligence": avg_emotional,
                        "overall": avg_overall,
                    },
                    "question_type_performance": question_type_performance,
                    "difficulty_performance": difficulty_performance,
                    "performance_data": performance_data,
                },
                "filters": {
                    "candidate_id": candidate_id,
                    "job_title": job_title,
                    "days": days,
                },
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mock_interview_bp.route("/health", methods=["GET"])
async def health_check():
    """Health check endpoint"""
    try:
        # Check Firebase health
        firebase_health = firebase_health_check()

        # Check if services are working
        health_status = {
            "status": (
                "healthy" if firebase_health["firebase_connected"] else "unhealthy"
            ),
            "timestamp": datetime.now().isoformat(),
            "services": {
                "whisper_model": "loaded" if service.whisper_model else "not_loaded",
                "gemini_client": (
                    "connected" if service.gemini_client else "not_connected"
                ),
                "tts_engine": (
                    "initialized" if service.tts_engine else "not_initialized"
                ),
                "firebase": (
                    "connected"
                    if firebase_health["firebase_connected"]
                    else "not_connected"
                ),
            },
            "firebase_details": firebase_health,
        }

        return jsonify(health_status)
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@mock_interview_bp.route("/user/<candidate_id>/sessions", methods=["GET"])
async def get_user_sessions_endpoint(candidate_id):
    """Get all sessions for a specific user"""
    try:
        # Get sessions for the user
        sessions = get_user_sessions(candidate_id)

        # Format sessions
        formatted_sessions = []
        for session_data in sessions:
            session = InterviewSession(**session_data)
            formatted_sessions.append(
                {
                    "session_id": session.id,
                    "job_title": session.job_title,
                    "status": session.status.value,
                    "created_at": session.created_at.isoformat(),
                    "started_at": (
                        session.started_at.isoformat() if session.started_at else None
                    ),
                    "completed_at": (
                        session.completed_at.isoformat()
                        if session.completed_at
                        else None
                    ),
                    "questions_asked": len(session.questions_asked),
                    "answers_count": len(session.answers),
                }
            )

        # Sort by creation date (newest first)
        formatted_sessions.sort(key=lambda x: x["created_at"], reverse=True)

        return jsonify(
            {
                "candidate_id": candidate_id,
                "sessions": formatted_sessions,
                "total": len(formatted_sessions),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
