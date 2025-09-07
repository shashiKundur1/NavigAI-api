# src/navigai_api/services/interview_service.py
"""
Interview business logic service for the NavigAI system
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid

from models.interview import (
    InterviewSession,
    InterviewStatus,
    InterviewQuestion,
    CandidateResponse,
    InterviewReport,
    QuestionType,
    DifficultyLevel,
)
from db import (
    save_interview_session,
    get_interview_session,
    update_interview_session,
    save_interview_report,
    get_interview_report,
)
from .livekit_service import LiveKitService
from .gemini_service import GeminiService

logger = logging.getLogger(__name__)


class InterviewService:
    """Service for managing interview sessions and business logic"""

    def __init__(self):
        self.livekit_service = LiveKitService()
        self.gemini_service = GeminiService()

    async def create_interview_session(
        self,
        user_id: str,
        job_title: str,
        job_description: str = "",
        company_name: str = "",
        interview_type: str = "general",
        difficulty: str = "medium",
        estimated_duration: int = 1800,  # 30 minutes
        max_questions: int = 10,
    ) -> Dict[str, Any]:
        """Create a new interview session"""
        try:
            # Create interview session
            session = InterviewSession(
                user_id=user_id,
                job_title=job_title,
                job_description=job_description,
                company_name=company_name,
                interview_type=interview_type,
                estimated_duration=estimated_duration,
                max_questions=max_questions,
                difficulty_level=DifficultyLevel(difficulty),
            )

            # Generate unique room name
            room_name = f"interview_{session.id}_{int(datetime.utcnow().timestamp())}"
            session.livekit_room_name = room_name

            # Create LiveKit room
            await self.livekit_service.create_room(room_name)

            # Generate participant tokens
            candidate_token = await self.livekit_service.generate_participant_token(
                room_name=room_name,
                participant_name=f"candidate_{user_id}",
                is_interviewer=False,
            )

            interviewer_token = await self.livekit_service.generate_participant_token(
                room_name=room_name,
                participant_name=f"interviewer_{session.id}",
                is_interviewer=True,
            )

            session.livekit_participant_token = candidate_token

            # Save session to Firebase
            await save_interview_session(session)

            logger.info(f"Created interview session {session.id} for user {user_id}")

            return {
                "session_id": session.id,
                "room_name": room_name,
                "candidate_token": candidate_token,
                "interviewer_token": interviewer_token,
                "estimated_duration": estimated_duration,
                "max_questions": max_questions,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error creating interview session: {e}")
            raise

    async def start_interview_session(self, session_id: str) -> Dict[str, Any]:
        """Start an interview session"""
        try:
            # Get session from database
            session = await get_interview_session(session_id)
            if not session:
                raise ValueError(f"Interview session {session_id} not found")

            # Check if session can be started
            if session.status != InterviewStatus.CREATED:
                raise ValueError(
                    f"Interview session is in {session.status.value} state, cannot start"
                )

            # Update session status
            session.status = InterviewStatus.IN_PROGRESS
            session.started_at = datetime.utcnow()
            session.updated_at = datetime.utcnow()

            # Generate interview questions using Gemini AI
            questions_text = await self.gemini_service.generate_interview_questions(
                job_title=session.job_title,
                job_description=session.job_description,
                difficulty=session.difficulty_level.value,
                count=session.max_questions,
            )

            # Convert to InterviewQuestion objects
            for i, question_text in enumerate(questions_text):
                question = InterviewQuestion(
                    question_text=question_text,
                    question_type=self._determine_question_type(question_text),
                    difficulty=session.difficulty_level,
                    expected_duration=300,  # 5 minutes per question
                )
                session.questions.append(question)

            # Start LiveKit agent
            agent_id = await self.livekit_service.start_interview_agent(session)

            # Store agent reference in session context
            session.conversation_context["agent_id"] = agent_id

            # Update session in database
            await update_interview_session(session)

            logger.info(f"Started interview session {session_id}")

            return {
                "session_id": session_id,
                "status": session.status.value,
                "started_at": session.started_at.isoformat(),
                "questions_generated": len(session.questions),
                "agent_id": agent_id,
                "first_question": (
                    session.questions[0].question_text if session.questions else None
                ),
            }

        except Exception as e:
            logger.error(f"Error starting interview session {session_id}: {e}")
            raise

    async def record_candidate_response(
        self,
        session_id: str,
        question_id: str,
        response_text: str,
        response_audio_url: Optional[str] = None,
        response_duration: int = 0,
    ) -> Dict[str, Any]:
        """Record candidate's response to a question"""
        try:
            # Get session from database
            session = await get_interview_session(session_id)
            if not session:
                raise ValueError(f"Interview session {session_id} not found")

            # Create candidate response
            response = CandidateResponse(
                question_id=question_id,
                response_text=response_text,
                response_audio_url=response_audio_url,
                response_duration=response_duration,
            )

            # Analyze response using Gemini AI
            question_text = ""
            for q in session.questions:
                if q.id == question_id:
                    question_text = q.question_text
                    break

            if question_text:
                analysis = await self.gemini_service.analyze_candidate_response(
                    question=question_text,
                    response=response_text,
                    job_requirements=session.job_description,
                )

                # Update response with analysis
                response.confidence_score = analysis.get("overall_score", 0.0)
                response.keywords_mentioned = analysis.get("keywords_mentioned", [])
                response.sentiment_score = analysis.get("confidence_score", 0.0)

            # Add response to session
            session.responses.append(response)
            session.updated_at = datetime.utcnow()

            # Update question index
            session.current_question_index += 1

            # Update session in database
            await update_interview_session(session)

            logger.info(
                f"Recorded response for session {session_id}, question {question_id}"
            )

            return {
                "response_recorded": True,
                "analysis": analysis if question_text else None,
                "current_question_index": session.current_question_index,
                "total_questions": len(session.questions),
                "interview_progress": (
                    session.current_question_index / len(session.questions)
                )
                * 100,
            }

        except Exception as e:
            logger.error(f"Error recording response for session {session_id}: {e}")
            raise

    async def complete_interview_session(self, session_id: str) -> Dict[str, Any]:
        """Complete an interview session and generate report"""
        try:
            # Get session from database
            session = await get_interview_session(session_id)
            if not session:
                raise ValueError(f"Interview session {session_id} not found")

            # Update session status
            session.status = InterviewStatus.COMPLETED
            session.completed_at = datetime.utcnow()
            session.actual_duration = (
                int((session.completed_at - session.started_at).total_seconds())
                if session.started_at
                else 0
            )
            session.updated_at = datetime.utcnow()

            # Stop LiveKit agent
            agent_id = session.conversation_context.get("agent_id")
            if agent_id:
                await self.livekit_service.stop_interview_agent(agent_id)

            # Generate comprehensive report
            report = await self._generate_interview_report(session)

            # Save report to database
            await save_interview_report(report)

            # Update session in database
            await update_interview_session(session)

            logger.info(f"Completed interview session {session_id}")

            return {
                "session_id": session_id,
                "status": session.status.value,
                "completed_at": session.completed_at.isoformat(),
                "actual_duration": session.actual_duration,
                "total_questions": len(session.questions),
                "total_responses": len(session.responses),
                "report_id": report.id,
                "overall_score": report.overall_score,
            }

        except Exception as e:
            logger.error(f"Error completing interview session {session_id}: {e}")
            raise

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current status of an interview session"""
        try:
            session = await get_interview_session(session_id)
            if not session:
                raise ValueError(f"Interview session {session_id} not found")

            # Calculate progress
            progress = 0
            if session.questions:
                progress = (
                    session.current_question_index / len(session.questions)
                ) * 100

            # Calculate elapsed time
            elapsed_time = 0
            if session.started_at:
                if session.completed_at:
                    elapsed_time = int(
                        (session.completed_at - session.started_at).total_seconds()
                    )
                else:
                    elapsed_time = int(
                        (datetime.utcnow() - session.started_at).total_seconds()
                    )

            return {
                "session_id": session_id,
                "status": session.status.value,
                "progress_percentage": progress,
                "current_question_index": session.current_question_index,
                "total_questions": len(session.questions),
                "elapsed_time_seconds": elapsed_time,
                "estimated_duration": session.estimated_duration,
                "started_at": (
                    session.started_at.isoformat() if session.started_at else None
                ),
                "completed_at": (
                    session.completed_at.isoformat() if session.completed_at else None
                ),
                "room_name": session.livekit_room_name,
                "next_question": self._get_next_question(session),
            }

        except Exception as e:
            logger.error(f"Error getting session status {session_id}: {e}")
            raise

    async def pause_interview_session(self, session_id: str) -> Dict[str, Any]:
        """Pause an interview session"""
        try:
            session = await get_interview_session(session_id)
            if not session:
                raise ValueError(f"Interview session {session_id} not found")

            if session.status != InterviewStatus.IN_PROGRESS:
                raise ValueError(
                    f"Cannot pause session in {session.status.value} state"
                )

            session.status = InterviewStatus.PAUSED
            session.updated_at = datetime.utcnow()

            # Pause LiveKit agent (implementation depends on agent design)
            # For now, just update status

            await update_interview_session(session)

            logger.info(f"Paused interview session {session_id}")

            return {
                "session_id": session_id,
                "status": session.status.value,
                "paused_at": session.updated_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error pausing session {session_id}: {e}")
            raise

    async def resume_interview_session(self, session_id: str) -> Dict[str, Any]:
        """Resume a paused interview session"""
        try:
            session = await get_interview_session(session_id)
            if not session:
                raise ValueError(f"Interview session {session_id} not found")

            if session.status != InterviewStatus.PAUSED:
                raise ValueError(
                    f"Cannot resume session in {session.status.value} state"
                )

            session.status = InterviewStatus.IN_PROGRESS
            session.updated_at = datetime.utcnow()

            await update_interview_session(session)

            logger.info(f"Resumed interview session {session_id}")

            return {
                "session_id": session_id,
                "status": session.status.value,
                "resumed_at": session.updated_at.isoformat(),
                "next_question": self._get_next_question(session),
            }

        except Exception as e:
            logger.error(f"Error resuming session {session_id}: {e}")
            raise

    def _determine_question_type(self, question_text: str) -> QuestionType:
        """Determine question type based on question text"""
        question_lower = question_text.lower()

        # Behavioral questions
        if any(
            phrase in question_lower
            for phrase in [
                "tell me about a time",
                "describe a situation",
                "give me an example",
            ]
        ):
            return QuestionType.BEHAVIORAL

        # Technical questions
        if any(
            phrase in question_lower
            for phrase in ["how would you", "what is your experience with", "technical"]
        ):
            return QuestionType.TECHNICAL

        # Situational questions
        if any(
            phrase in question_lower
            for phrase in ["what would you do if", "how would you handle", "imagine"]
        ):
            return QuestionType.SITUATIONAL

        # Default to general
        return QuestionType.GENERAL

    def _get_next_question(self, session: InterviewSession) -> Optional[str]:
        """Get the next question for the interview"""
        if session.current_question_index < len(session.questions):
            return session.questions[session.current_question_index].question_text
        return None

    async def _generate_interview_report(
        self, session: InterviewSession
    ) -> InterviewReport:
        """Generate comprehensive interview report"""
        try:
            # Prepare data for report generation
            questions = [q.question_text for q in session.questions]
            responses = [r.response_text for r in session.responses]

            # Get individual question scores
            individual_scores = []
            for response in session.responses:
                individual_scores.append(
                    {
                        "question_id": response.question_id,
                        "overall_score": response.confidence_score,
                        "keywords": response.keywords_mentioned,
                    }
                )

            # Generate report using Gemini AI
            report_data = await self.gemini_service.generate_interview_report(
                questions=questions,
                responses=responses,
                individual_scores=individual_scores,
                interview_context={
                    "job_title": session.job_title,
                    "company_name": session.company_name,
                    "interview_type": session.interview_type,
                },
            )

            # Create report object
            report = InterviewReport(
                interview_session_id=session.id,
                user_id=session.user_id,
                overall_score=report_data.get("overall_score", 70.0),
                communication_score=report_data.get("communication_score", 70.0),
                technical_score=report_data.get("technical_score", 70.0),
                behavioral_score=report_data.get("behavioral_score", 70.0),
                strengths=report_data.get("strengths", []),
                weaknesses=report_data.get("weaknesses", []),
                recommendations=report_data.get("recommendations", []),
                average_response_time=self._calculate_average_response_time(session),
                total_speaking_time=sum(r.response_duration for r in session.responses),
                fluency_score=report_data.get("overall_score", 70.0),  # Simplified
                vocabulary_complexity=report_data.get(
                    "overall_score", 70.0
                ),  # Simplified
            )

            return report

        except Exception as e:
            logger.error(f"Error generating interview report: {e}")
            # Return basic report
            return InterviewReport(
                interview_session_id=session.id,
                user_id=session.user_id,
                overall_score=70.0,
                communication_score=70.0,
                technical_score=70.0,
                behavioral_score=70.0,
                strengths=["Completed interview"],
                weaknesses=["Analysis unavailable"],
                recommendations=["Schedule follow-up interview"],
            )

    def _calculate_average_response_time(self, session: InterviewSession) -> float:
        """Calculate average response time"""
        if not session.responses:
            return 0.0

        total_time = sum(r.response_duration for r in session.responses)
        return total_time / len(session.responses)
