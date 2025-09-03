# src/navigai_api/services/livekit_service.py
"""
LiveKit service for managing real-time voice AI agents
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

import livekit
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import google, silero
from livekit import api

from core.settings import Settings
from ..models.interview import InterviewSession, InterviewStatus
from .gemini_service import GeminiService

logger = logging.getLogger(__name__)


class LiveKitService:
    """Service for managing LiveKit agents and sessions"""

    def __init__(self):
        self.livekit_url = os.getenv("LIVEKIT_URL")
        self.api_key = os.getenv("LIVEKIT_API_KEY")
        self.api_secret = os.getenv("LIVEKIT_API_SECRET")
        self.gemini_service = GeminiService()
        self.active_agents: Dict[str, Any] = {}

        # Initialize LiveKit API client
        if self.livekit_url and self.api_key and self.api_secret:
            self.livekit_api = api.LiveKitAPI(
                url=self.livekit_url, api_key=self.api_key, api_secret=self.api_secret
            )
        else:
            logger.warning("LiveKit credentials not found in environment variables")
            self.livekit_api = None

    def health_check(self) -> Dict[str, Any]:
        """Check LiveKit service health"""
        try:
            if not self.livekit_api:
                return {"status": "error", "message": "LiveKit API not initialized"}

            return {
                "status": "healthy",
                "active_agents": len(self.active_agents),
                "url": self.livekit_url,
            }
        except Exception as e:
            logger.error(f"LiveKit health check failed: {e}")
            return {"status": "error", "message": str(e)}

    async def create_room(self, room_name: str) -> Dict[str, Any]:
        """Create a new LiveKit room for interview session"""
        try:
            if not self.livekit_api:
                raise Exception("LiveKit API not initialized")

            room_opts = api.CreateRoomRequest(name=room_name)
            room = await self.livekit_api.room.create_room(room_opts)

            logger.info(f"Created LiveKit room: {room_name}")
            return {
                "room_name": room.name,
                "creation_time": room.creation_time,
                "status": "created",
            }
        except Exception as e:
            logger.error(f"Failed to create LiveKit room: {e}")
            raise

    async def generate_participant_token(
        self, room_name: str, participant_name: str, is_interviewer: bool = False
    ) -> str:
        """Generate participant token for room access"""
        try:
            if not self.api_key or not self.api_secret:
                raise Exception("LiveKit API credentials not available")

            # Set permissions based on role
            permissions = api.VideoGrant(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )

            # Add additional permissions for interviewer (AI agent)
            if is_interviewer:
                permissions.room_admin = True
                permissions.room_create = True

            token = api.AccessToken(self.api_key, self.api_secret)
            token.with_identity(participant_name)
            token.with_grants(permissions)

            jwt_token = token.to_jwt()
            logger.info(f"Generated token for {participant_name} in room {room_name}")

            return jwt_token
        except Exception as e:
            logger.error(f"Failed to generate participant token: {e}")
            raise

    async def start_agent(self) -> None:
        """Start the LiveKit agent worker"""
        try:
            # This would typically be run as a separate process
            # For now, we'll just mark it as started
            logger.info("LiveKit agent worker marked as started")
        except Exception as e:
            logger.error(f"Failed to start LiveKit agent: {e}")
            raise

    async def stop_agent(self) -> None:
        """Stop the LiveKit agent worker"""
        try:
            # Clean up active agents
            for agent_id in list(self.active_agents.keys()):
                await self.stop_interview_agent(agent_id)

            logger.info("LiveKit agent worker stopped")
        except Exception as e:
            logger.error(f"Failed to stop LiveKit agent: {e}")
            raise

    async def start_interview_agent(self, interview_session: InterviewSession) -> str:
        """Start an interview agent for a specific session"""
        try:
            room_name = interview_session.livekit_room_name
            agent_id = f"agent_{interview_session.id}"

            # Create agent with interview context
            agent_context = self._create_interview_context(interview_session)

            # Store agent reference
            self.active_agents[agent_id] = {
                "room_name": room_name,
                "interview_session_id": interview_session.id,
                "context": agent_context,
                "started_at": datetime.utcnow(),
            }

            logger.info(f"Started interview agent {agent_id} for room {room_name}")
            return agent_id

        except Exception as e:
            logger.error(f"Failed to start interview agent: {e}")
            raise

    async def stop_interview_agent(self, agent_id: str) -> None:
        """Stop a specific interview agent"""
        try:
            if agent_id in self.active_agents:
                agent_info = self.active_agents[agent_id]

                # Perform cleanup
                logger.info(f"Stopping interview agent {agent_id}")

                # Remove from active agents
                del self.active_agents[agent_id]

                logger.info(f"Interview agent {agent_id} stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop interview agent {agent_id}: {e}")
            raise

    def _create_interview_context(
        self, interview_session: InterviewSession
    ) -> Dict[str, Any]:
        """Create interview context for AI agent"""
        return {
            "job_title": interview_session.job_title,
            "job_description": interview_session.job_description,
            "company_name": interview_session.company_name,
            "interview_type": interview_session.interview_type,
            "difficulty_level": interview_session.difficulty_level.value,
            "max_questions": interview_session.max_questions,
            "ai_personality": interview_session.ai_personality,
            "current_question_index": interview_session.current_question_index,
            "conversation_context": interview_session.conversation_context,
        }


# Interview Agent Implementation
class InterviewAgent:
    """LiveKit Interview Agent with Gemini AI integration"""

    def __init__(self, interview_context: Dict[str, Any]):
        self.context = interview_context
        self.gemini_service = GeminiService()
        self.current_question_index = 0
        self.interview_questions = []

    @function_tool
    async def next_interview_question(
        self, context, candidate_response: str = ""
    ) -> str:
        """Move to the next interview question"""
        try:
            # If this is the first question, generate interview questions
            if not self.interview_questions:
                self.interview_questions = (
                    await self.gemini_service.generate_interview_questions(
                        job_title=self.context.get("job_title", ""),
                        job_description=self.context.get("job_description", ""),
                        difficulty=self.context.get("difficulty_level", "medium"),
                        count=self.context.get("max_questions", 10),
                    )
                )

            # Check if we have more questions
            if self.current_question_index >= len(self.interview_questions):
                return "Thank you for your time today. We've completed all the questions. We'll be in touch soon with next steps. Have a great day!"

            # Get the current question
            question = self.interview_questions[self.current_question_index]
            self.current_question_index += 1

            # Personalize the question delivery
            if self.current_question_index == 1:
                return f"Great! Let's start with the first question: {question}"
            else:
                return f"Thank you for that response. Let's move on to the next question: {question}"

        except Exception as e:
            logger.error(f"Error in next_interview_question: {e}")
            return "I apologize, but I'm having some technical difficulties. Let me ask you this: Can you tell me about yourself?"

    @function_tool
    async def provide_feedback(self, context, response_content: str) -> str:
        """Provide natural follow-up based on candidate response"""
        try:
            # Use Gemini to generate natural follow-up
            follow_up = await self.gemini_service.generate_follow_up_question(
                original_question=(
                    self.interview_questions[self.current_question_index - 1]
                    if self.interview_questions
                    else ""
                ),
                candidate_response=response_content,
                interview_context=self.context,
            )

            return follow_up

        except Exception as e:
            logger.error(f"Error in provide_feedback: {e}")
            return "That's interesting. Can you tell me more about that experience?"

    async def create_agent_session(self, room_name: str) -> AgentSession:
        """Create LiveKit agent session with Gemini integration"""
        try:
            # Create interview instructions
            instructions = self._create_interview_instructions()

            agent = Agent(
                instructions=instructions,
                tools=[self.next_interview_question, self.provide_feedback],
            )

            # Try using Gemini Live API first (most natural)
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
                        min_silence_duration=0.8,  # Allow thinking pauses
                        min_speaking_duration=0.3,
                    ),
                    stt=google.STT(
                        model="chirp", languages=["en-US"], spoken_punctuation=True
                    ),
                    llm=google.LLM(
                        model="gemini-2.0-flash-exp",
                        temperature=0.7,
                        max_output_tokens=200,  # Keep responses concise
                    ),
                    tts=google.TTS(
                        voice_name="en-US-Neural2-H", speaking_rate=0.9, pitch=0.0
                    ),
                )

            return session

        except Exception as e:
            logger.error(f"Failed to create agent session: {e}")
            raise

    def _create_interview_instructions(self) -> str:
        """Create personalized interview instructions for the AI agent"""
        job_title = self.context.get("job_title", "this position")
        company_name = self.context.get("company_name", "our company")
        interview_type = self.context.get("interview_type", "general")
        personality = self.context.get("ai_personality", "professional")

        base_instructions = f"""
You are a {personality} AI interviewer conducting a {interview_type} interview for the {job_title} position at {company_name}.

Your personality:
- Professional but warm and approachable
- Show genuine interest in candidate responses
- Ask thoughtful follow-up questions
- Use active listening techniques ("I see", "That's interesting", "Tell me more about that")
- Maintain natural conversation flow

Interview guidelines:
1. Start with a warm greeting and brief introduction
2. Ask questions one at a time
3. Allow natural pauses for candidate thinking
4. Ask clarifying follow-up questions when appropriate
5. Smoothly transition between topics
6. Show enthusiasm for good answers
7. End with next steps and thank the candidate

Communication style:
- Keep responses conversational and engaging
- Avoid robotic or scripted language
- Use natural speech patterns
- Show empathy and understanding
- Maintain professional boundaries

Remember: You're conducting a real interview that will impact someone's career. Be thorough but fair, professional but human.
"""

        return base_instructions.strip()
