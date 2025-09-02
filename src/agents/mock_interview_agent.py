import threading
import time
import os
import logging
from typing import Optional, Dict, Any, Callable
import customtkinter as ctk
from tkinter import messagebox
from models.mock_interview import InterviewSession, Question, Answer, InterviewStatus
from services.mock_interview_service import MockInterviewService
from core.settings import Settings

# Import our new services
from services.audio_analysis_service import AudioAnalysisService
from services.tts_service import TTSService
from services.question_generation_service import QuestionGenerationService
from services.thompson_sampling_service import ThompsonSamplingService
from services.report_generation_service import ReportGenerationService

# Set up logging
logger = logging.getLogger(__name__)


class MockInterviewAgent:
    """Main agent for coordinating the AI mock interview process"""

    def __init__(self):
        self.service = MockInterviewService()
        self.current_session: Optional[InterviewSession] = None
        self.current_question: Optional[Question] = None
        self.is_recording = False
        self.recording_thread = None
        self.gui = None
        self.recording_start_time = None
        self.silence_start_time = None
        self.audio_analysis_service = AudioAnalysisService()
        self.tts_service = TTSService()
        self.question_service = QuestionGenerationService()
        self.sampling_service = ThompsonSamplingService()
        self.report_service = ReportGenerationService()

        # Performance optimization flags
        self.is_processing = False
        self.next_question_pending = False

        # Track questions to ensure consistency
        self.questions_asked = []
        self.current_question_index = 0

    def create_interview_session(
        self, job_title: str, job_description: str, candidate_id: str
    ) -> str:
        """Create a new interview session"""
        try:
            session = self.service.create_interview_session(
                job_title, job_description, candidate_id
            )
            self.current_session = session
            self.questions_asked = []
            self.current_question_index = 0
            logger.info(
                f"Created interview session {session.id} for candidate {candidate_id}"
            )
            return session.id
        except Exception as e:
            logger.error(f"Failed to create interview session: {e}")
            raise

    def start_interview(self, session_id: str) -> bool:
        """Start the interview session"""
        try:
            success = self.service.start_interview(session_id)
            if success:
                from db.firebase_db import get_interview_session

                session_data = get_interview_session(session_id)
                if session_data:
                    self.current_session = InterviewSession(**session_data)
                    logger.info(f"Started interview session {session_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to start interview session {session_id}: {e}")
            return False

    def get_next_question(self) -> Optional[Question]:
        """Get the next question using advanced NLP"""
        if not self.current_session:
            logger.warning("No active session to get next question")
            return None

        try:
            # Get candidate's current performance
            candidate_performance = self._get_current_performance()

            # Generate contextual next question
            question = self.question_service.generate_contextual_next_question(
                job_description=self.current_session.job_description,
                conversation_history=self.service.conversation_history,
                asked_questions=self.questions_asked,
                candidate_performance=candidate_performance,
            )

            if question:
                # Add to asked questions
                self.questions_asked.append(question.id)
                self.current_question_index += 1
                self.current_question = question

                # Update session
                self.current_session.questions_asked.append(question.id)
                self.current_session.current_question_index = (
                    self.current_question_index
                )

                logger.info(f"Generated question: {question.text[:50]}...")
                return question

            return None
        except Exception as e:
            logger.error(f"Failed to generate next question: {e}")
            return None

    def _get_current_performance(self) -> Dict[str, float]:
        """Get current performance metrics for the candidate"""
        if not self.current_session or not self.current_session.answers:
            return {
                "technical_score": 0.5,
                "communication_score": 0.5,
                "confidence_score": 0.5,
            }

        latest_answer = self.current_session.answers[-1]
        return {
            "technical_score": latest_answer.technical_score,
            "communication_score": (
                latest_answer.fluency_score + latest_answer.confidence_score
            )
            / 2,
            "confidence_score": latest_answer.confidence_score,
        }

    def start_recording(self):
        """Start recording audio"""
        if not self.current_session:
            logger.warning("No active session to start recording")
            return False

        try:
            self.is_recording = True
            self.recording_start_time = time.time()
            self.silence_start_time = None
            self.service.start_audio_recording(self.current_session.id)
            logger.info("Started audio recording")
            return True
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.is_recording = False
            return False

    def check_silence_and_stop(self):
        """Check for silence and stop recording if detected"""
        if not self.is_recording or self.is_processing:
            return

        current_time = time.time()

        # Check for timeout
        recording_timeout = getattr(Settings, "RECORDING_TIMEOUT", 120)
        if current_time - self.recording_start_time > recording_timeout:
            logger.info("Recording timeout reached")
            self.stop_recording_and_analyze()
            return

        # Check for silence (simplified - in production, use actual audio analysis)
        if self.silence_start_time is None:
            # Start silence detection after minimum recording time
            if current_time - self.recording_start_time > 5.0:  # 5 seconds minimum
                self.silence_start_time = current_time
        else:
            # Check if silence threshold reached
            silence_threshold = getattr(Settings, "SILENCE_THRESHOLD", 3)
            if current_time - self.silence_start_time > silence_threshold:
                logger.info("Silence threshold reached")
                self.stop_recording_and_analyze()
                return

        # Schedule next check
        if self.gui:
            self.gui.root.after(1000, self.check_silence_and_stop)

    def stop_recording_and_analyze(self, callback: Optional[Callable] = None) -> None:
        """Stop recording and analyze the response with callback"""
        if not self.current_session or not self.current_question or self.is_processing:
            logger.warning(
                "Cannot process recording - already processing or no active session/question"
            )
            if callback:
                callback(None)
            return

        self.is_processing = True

        def process_in_thread():
            try:
                # Stop recording
                self.is_recording = False
                audio_file = self.service.stop_audio_recording()

                if not audio_file:
                    logger.error("No audio file returned after recording")
                    self.is_processing = False
                    if callback:
                        callback(None)
                    return

                # Transcribe audio
                transcribed_text = self.service.transcribe_audio(audio_file)
                logger.info(f"Transcribed audio: {transcribed_text[:50]}...")

                # Analyze response
                answer = self.service.analyze_response(
                    audio_file,
                    transcribed_text,
                    self.current_question,
                    self.current_session,
                )

                # Submit answer
                self.service.submit_answer(self.current_session.id, answer)
                logger.info("Submitted answer for analysis")

                # Clean up audio file
                if os.path.exists(audio_file):
                    os.remove(audio_file)

                result = {
                    "transcribed_text": transcribed_text,
                    "answer": answer,
                    "scores": {
                        "technical": answer.technical_score,
                        "communication": (
                            answer.fluency_score + answer.confidence_score
                        )
                        / 2,
                        "confidence": answer.confidence_score,
                        "sentiment": answer.sentiment_score,
                    },
                }

                # Reset processing flag
                self.is_processing = False

                # Call callback with result
                if callback:
                    callback(result)

            except Exception as e:
                logger.error(f"Error during recording analysis: {e}")
                self.is_processing = False
                if callback:
                    callback(None)

        # Start processing in a separate thread to avoid blocking
        thread = threading.Thread(target=process_in_thread)
        thread.daemon = True
        thread.start()

    def should_end_interview(self) -> bool:
        """Check if interview should be ended"""
        if not self.current_session:
            return True

        try:
            should_end = self.service.should_end_interview(self.current_session.id)
            if should_end:
                logger.info("Interview should be ended")
            return should_end
        except Exception as e:
            logger.error(f"Error checking if interview should end: {e}")
            return True

    def end_interview(self) -> bool:
        """End the interview and generate report"""
        if not self.current_session:
            logger.warning("No active session to end")
            return False

        try:
            # End interview session
            success = self.service.end_interview(self.current_session.id)

            if success:
                # Generate report
                report_path = self.service.generate_interview_report(
                    self.current_session.id
                )
                logger.info(f"Generated report at {report_path}")

                if report_path and self.gui:
                    # Show success message
                    self.gui.show_report_generated(report_path)

            return success
        except Exception as e:
            logger.error(f"Error ending interview: {e}")
            return False

    def text_to_speech(self, text: str, callback: Optional[Callable] = None):
        """Convert text to speech with optional callback"""

        def speak():
            try:
                # Wait for any ongoing TTS to finish
                while self.tts_service.is_busy():
                    time.sleep(0.1)

                self.tts_service.text_to_speech(text, blocking=False, callback=callback)
            except Exception as e:
                logger.error(f"Error in text-to-speech: {e}")
                if callback:
                    callback()

        # Run in separate thread to avoid blocking GUI
        thread = threading.Thread(target=speak)
        thread.daemon = True
        thread.start()

    def get_session_progress(self) -> Dict[str, Any]:
        """Get current session progress"""
        if not self.current_session:
            return {}

        try:
            return {
                "questions_asked": len(self.questions_asked),
                "current_question": (
                    self.current_question.text if self.current_question else None
                ),
                "status": self.current_session.status.value,
                "answers_count": len(self.current_session.answers),
            }
        except Exception as e:
            logger.error(f"Error getting session progress: {e}")
            return {}

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for current session"""
        if not self.current_session or not self.current_session.answers:
            return {}

        try:
            latest_answer = self.current_session.answers[-1]
            return {
                "latest_technical_score": latest_answer.technical_score,
                "latest_communication_score": (
                    latest_answer.fluency_score + latest_answer.confidence_score
                )
                / 2,
                "latest_confidence_score": latest_answer.confidence_score,
                "average_technical_score": sum(
                    a.technical_score for a in self.current_session.answers
                )
                / len(self.current_session.answers),
            }
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
