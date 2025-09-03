# src/navigai_api/agents/interview_agent.py
"""
LiveKit Interview Agent implementation for NavigAI
This is the main agent that runs the interview conversations
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import google, silero
from livekit import rtc

from src.services.gemini_service import GeminiService
from db.firebase_db import get_interview_session, update_interview_session
from src.models.interview import InterviewStatus, CandidateResponse

logger = logging.getLogger(__name__)


class NavigAIInterviewAgent:
    """Main interview agent that conducts live interviews"""

    def __init__(self, interview_session_id: str):
        self.session_id = interview_session_id
        self.gemini_service = GeminiService()
        self.current_question_index = 0
        self.interview_questions = []
        self.session_data = None

        # Agent state
        self.is_active = False
        self.conversation_history = []

    async def initialize(self) -> None:
        """Initialize the agent with interview session data"""
        try:
            # Load interview session from database
            self.session_data = await get_interview_session(self.session_id)
            if not self.session_data:
                raise ValueError(f"Interview session {self.session_id} not found")

            # Generate interview questions using Gemini
            self.interview_questions = (
                await self.gemini_service.generate_interview_questions(
                    job_title=self.session_data.job_title,
                    job_description=self.session_data.job_description,
                    difficulty=self.session_data.difficulty_level.value,
                    count=self.session_data.max_questions,
                )
            )

            self.current_question_index = self.session_data.current_question_index

            logger.info(f"Interview agent initialized for session {self.session_id}")

        except Exception as e:
            logger.error(f"Error initializing interview agent: {e}")
            raise

    @function_tool
    async def ask_next_question(self, context, candidate_response: str = "") -> str:
        """Ask the next interview question"""
        try:
            # Record previous response if provided
            if candidate_response.strip() and self.current_question_index > 0:
                await self._record_candidate_response(candidate_response)

            # Check if we have more questions
            if self.current_question_index >= len(self.interview_questions):
                await self._complete_interview()
                return self._get_closing_message()

            # Get current question
            question = self.interview_questions[self.current_question_index]

            # Format question based on interview stage
            formatted_question = self._format_question(
                question, self.current_question_index
            )

            # Update conversation history
            self.conversation_history.append(
                {
                    "type": "question",
                    "content": question,
                    "index": self.current_question_index,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            # Move to next question for next call
            self.current_question_index += 1

            return formatted_question

        except Exception as e:
            logger.error(f"Error in ask_next_question: {e}")
            return "I apologize for the technical difficulty. Let me ask you this: Can you tell me about yourself and your background?"

    @function_tool
    async def provide_follow_up(self, context, response_content: str) -> str:
        """Provide natural follow-up based on candidate response"""
        try:
            # Get the last question asked
            last_question = ""
            if self.current_question_index > 0 and self.interview_questions:
                last_question = self.interview_questions[
                    self.current_question_index - 1
                ]

            # Generate intelligent follow-up using Gemini
            follow_up = await self.gemini_service.generate_follow_up_question(
                original_question=last_question,
                candidate_response=response_content,
                interview_context={
                    "job_title": self.session_data.job_title,
                    "company_name": self.session_data.company_name,
                    "interview_type": self.session_data.interview_type,
                },
            )

            # Update conversation history
            self.conversation_history.append(
                {
                    "type": "follow_up",
                    "content": follow_up,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            return follow_up

        except Exception as e:
            logger.error(f"Error in provide_follow_up: {e}")
            return "That's very interesting. Can you elaborate on that experience a bit more?"

    @function_tool
    async def acknowledge_response(self, context, response_content: str) -> str:
        """Acknowledge candidate response with active listening"""
        try:
            # Generate natural acknowledgment
            acknowledgments = [
                "I see. That's a great example.",
                "That's really interesting.",
                "Thank you for sharing that.",
                "That sounds like valuable experience.",
                "I appreciate you walking me through that.",
                "That's a thoughtful approach.",
                "That's exactly the kind of insight I was looking for.",
            ]

            # Simple logic to vary acknowledgments
            ack_index = len(self.conversation_history) % len(acknowledgments)
            acknowledgment = acknowledgments[ack_index]

            # Record the response
            await self._record_candidate_response(response_content)

            return acknowledgment

        except Exception as e:
            logger.error(f"Error in acknowledge_response: {e}")
            return "Thank you for that response."

    async def create_agent_session(self, room_name: str) -> AgentSession:
        """Create the LiveKit agent session"""
        try:
            # Create interview instructions
            instructions = self._create_interview_instructions()

            # Create agent with tools
            agent = Agent(
                instructions=instructions,
                tools=[
                    self.ask_next_question,
                    self.provide_follow_up,
                    self.acknowledge_response,
                ],
            )

            # Try Gemini Live API first (most natural)
            try:
                session = AgentSession(
                    llm=google.beta.realtime.RealtimeModel(
                        model="gemini-2.0-flash-exp",
                        voice="Puck",  # Professional voice
                        temperature=0.7,
                        instructions=instructions,
                    )
                )
                logger.info("Using Gemini Live API for real-time conversation")

            except Exception as e:
                logger.warning(f"Gemini Live API not available, using pipeline: {e}")

                # Fallback to pipeline approach
                session = AgentSession(
                    vad=silero.VAD.load(
                        min_silence_duration=1.0,  # Allow thinking time
                        min_speaking_duration=0.3,
                    ),
                    stt=google.STT(
                        model="chirp",
                        languages=["en-US"],
                        spoken_punctuation=True,
                        enable_automatic_punctuation=True,
                    ),
                    llm=google.LLM(
                        model="gemini-2.0-flash-exp",
                        temperature=0.7,
                        max_output_tokens=150,  # Concise responses
                    ),
                    tts=google.TTS(
                        voice_name="en-US-Neural2-H",  # Professional female voice
                        speaking_rate=0.9,
                        pitch=0.0,
                    ),
                )

            return session

        except Exception as e:
            logger.error(f"Error creating agent session: {e}")
            raise

    def _create_interview_instructions(self) -> str:
        """Create personalized instructions for the AI interviewer"""
        job_title = self.session_data.job_title
        company_name = self.session_data.company_name or "our company"
        interview_type = self.session_data.interview_type

        instructions = f"""
You are a professional AI interviewer conducting a {interview_type} interview for the {job_title} position at {company_name}.

Your Role:
- Act as an experienced, empathetic interviewer
- Create a comfortable, conversational atmosphere
- Show genuine interest in the candidate's responses
- Ask thoughtful follow-up questions
- Provide encouragement and positive feedback

Conversation Style:
- Be warm but professional
- Use natural speech patterns
- Show active listening with phrases like "I see", "That's interesting"
- Allow natural pauses for candidate thinking
- Ask one question at a time
- Keep responses conversational (not robotic)

Interview Flow:
1. Start with a warm greeting and brief introduction
2. Explain the interview format briefly
3. Ask questions using your tools
4. Listen actively and ask follow-ups when appropriate
5. Smoothly transition between questions
6. End with next steps and appreciation

Communication Guidelines:
- Keep responses between 1-3 sentences
- Avoid long monologues
- Show enthusiasm for good answers
- Be encouraging if candidate seems nervous
- Maintain professional but friendly tone
- Ask for clarification if responses are unclear

Remember: This is a real interview that impacts someone's career. Be thorough, fair, and human.
"""

        return instructions.strip()

    def _format_question(self, question: str, question_index: int) -> str:
        """Format question based on interview stage"""
        if question_index == 0:
            return f"Great! Let's start with our first question: {question}"
        elif question_index == 1:
            return f"Thank you for that introduction. Now, {question}"
        else:
            transitions = [
                "Let's move on to the next question:",
                "I'd like to ask you about:",
                "Moving forward,",
                "Next, I'm curious about:",
                "Another question I have is:",
            ]
            transition = transitions[question_index % len(transitions)]
            return f"{transition} {question}"

    def _get_closing_message(self) -> str:
        """Get closing message for interview completion"""
        messages = [
            "Thank you so much for your time today. This has been a really insightful conversation. We'll review everything and be in touch with next steps within the next few days. Do you have any final questions for me?",
            "That completes our interview questions. I really appreciated getting to know more about your background and experience. We'll be making our decision soon and will reach out with updates. Is there anything else you'd like to share?",
            "We've covered all the questions I had prepared. Thank you for the thoughtful responses - it's been great learning about your experience. We'll be in touch soon about next steps. Any final questions from your side?",
        ]

        # Vary based on session
        message_index = len(self.conversation_history) % len(messages)
        return messages[message_index]

    async def _record_candidate_response(self, response_text: str) -> None:
        """Record candidate response to database"""
        try:
            if not self.session_data or not response_text.strip():
                return

            # Create response object
            response = CandidateResponse(
                question_id=f"q_{self.current_question_index - 1}",
                response_text=response_text,
                response_duration=0,  # Would be calculated from audio
                timestamp=datetime.utcnow(),
            )

            # Add to session data
            self.session_data.responses.append(response)
            self.session_data.updated_at = datetime.utcnow()

            # Update in database
            await update_interview_session(self.session_data)

            logger.info(f"Recorded response for session {self.session_id}")

        except Exception as e:
            logger.error(f"Error recording candidate response: {e}")

    async def _complete_interview(self) -> None:
        """Complete the interview session"""
        try:
            if not self.session_data:
                return

            # Update session status
            self.session_data.status = InterviewStatus.COMPLETED
            self.session_data.completed_at = datetime.utcnow()
            self.session_data.actual_duration = (
                int(
                    (
                        self.session_data.completed_at - self.session_data.started_at
                    ).total_seconds()
                )
                if self.session_data.started_at
                else 0
            )

            # Save final state
            await update_interview_session(self.session_data)

            logger.info(f"Interview session {self.session_id} completed")

        except Exception as e:
            logger.error(f"Error completing interview: {e}")


# LiveKit Agent Entry Point
async def entrypoint(ctx: JobContext):
    """Main entry point for LiveKit agent"""
    try:
        await ctx.connect()

        # Get interview session ID from room metadata or name
        room_name = ctx.room.name
        session_id = room_name.split("_")[1] if "_" in room_name else None

        if not session_id:
            logger.error("No session ID found in room name")
            return

        # Create and initialize interview agent
        interview_agent = NavigAIInterviewAgent(session_id)
        await interview_agent.initialize()

        # Create agent session
        session = await interview_agent.create_agent_session(room_name)

        # Start the interview
        await session.start(room=ctx.room)

        # Initial greeting
        await session.generate_reply(
            instructions=f"""
            Greet the candidate warmly. Introduce yourself as their AI interviewer. 
            Ask how they're doing today and if they're ready to begin. 
            Keep it brief and natural - like a real interviewer would.
            """
        )

        logger.info(f"Interview agent started for session {session_id}")

    except Exception as e:
        logger.error(f"Error in agent entrypoint: {e}")
        raise


if __name__ == "__main__":
    # Run the agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint, prewarm_connections=True, log_level="INFO"
        )
    )
