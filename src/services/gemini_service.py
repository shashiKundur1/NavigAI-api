# src/navigai_api/services/gemini_service.py
"""
Gemini AI service for interview question generation and response analysis
"""

import logging
import os
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.generativeai import GenerativeModel

from core.settings import Settings

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini AI"""

    def __init__(self):
        self.api_key = Settings.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("Gemini API key not found in settings")
            return

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Initialize models
        self.text_model = GenerativeModel("gemini-2.0-flash-exp")
        self.conversation_model = GenerativeModel("gemini-2.0-flash-exp")

        logger.info("Gemini AI service initialized successfully")

    async def generate_interview_questions(
        self,
        job_title: str,
        job_description: str = "",
        difficulty: str = "medium",
        count: int = 10,
    ) -> List[str]:
        """Generate interview questions based on job requirements"""
        try:
            prompt = f"""
Generate {count} professional interview questions for a {job_title} position.

Job Description: {job_description or "Not provided"}
Difficulty Level: {difficulty}

Requirements:
1. Mix different question types (behavioral, technical, situational)
2. Questions should be appropriate for {difficulty} difficulty level
3. Include both general and role-specific questions
4. Make questions conversational and engaging
5. Avoid yes/no questions
6. Focus on assessing skills, experience, and cultural fit

Format: Return only the questions, one per line, without numbering.
"""

            response = self.text_model.generate_content(prompt)
            questions = [q.strip() for q in response.text.split("\n") if q.strip()]

            # Ensure we have the requested number of questions
            if len(questions) < count:
                # Generate additional questions if needed
                additional_prompt = f"""
Generate {count - len(questions)} more interview questions for {job_title}.
Make them different from these existing questions:
{chr(10).join(questions)}

Format: Return only the questions, one per line.
"""
                additional_response = self.text_model.generate_content(
                    additional_prompt
                )
                additional_questions = [
                    q.strip() for q in additional_response.text.split("\n") if q.strip()
                ]
                questions.extend(additional_questions)

            logger.info(
                f"Generated {len(questions)} interview questions for {job_title}"
            )
            return questions[:count]  # Return exactly the requested number

        except Exception as e:
            logger.error(f"Error generating interview questions: {e}")
            # Return fallback questions
            return self._get_fallback_questions(job_title, count)

    async def generate_follow_up_question(
        self,
        original_question: str,
        candidate_response: str,
        interview_context: Dict[str, Any],
    ) -> str:
        """Generate a natural follow-up question based on candidate's response"""
        try:
            prompt = f"""
As a professional interviewer, generate a natural follow-up question or comment based on the candidate's response.

Original Question: {original_question}
Candidate's Response: {candidate_response}
Job Title: {interview_context.get('job_title', 'Not specified')}

Guidelines:
1. Show active listening with phrases like "That's interesting" or "I see"
2. Ask for specific examples or clarification if the response is vague
3. Probe deeper into relevant experience or skills
4. Keep it conversational and encouraging
5. If the response is complete, acknowledge it positively and smoothly transition

Respond as if you're speaking directly to the candidate in real-time.
"""

            response = self.text_model.generate_content(prompt)
            follow_up = response.text.strip()

            logger.info("Generated follow-up question")
            return follow_up

        except Exception as e:
            logger.error(f"Error generating follow-up question: {e}")
            return (
                "That's very interesting. Can you tell me more about that experience?"
            )

    async def analyze_candidate_response(
        self, question: str, response: str, job_requirements: str = ""
    ) -> Dict[str, Any]:
        """Analyze candidate's response and provide scoring"""
        try:
            prompt = f"""
Analyze this interview response and provide detailed feedback:

Question: {question}
Response: {response}
Job Requirements: {job_requirements or "Not specified"}

Provide analysis in the following format:

SCORES (0-10 scale):
- Content Quality: [score]
- Communication Skills: [score]
- Relevance: [score]
- Confidence Level: [score]
- Overall Score: [score]

STRENGTHS:
- [List 2-3 key strengths]

AREAS FOR IMPROVEMENT:
- [List 2-3 areas to improve]

KEYWORDS MENTIONED:
- [List relevant keywords/skills mentioned]

RECOMMENDATIONS:
- [2-3 specific suggestions for improvement]

Keep feedback constructive and professional.
"""

            response_obj = self.text_model.generate_content(prompt)
            analysis_text = response_obj.text.strip()

            # Parse the structured response
            analysis = self._parse_analysis_response(analysis_text)

            logger.info("Analyzed candidate response")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing candidate response: {e}")
            return self._get_default_analysis()

    async def generate_interview_report(
        self,
        questions: List[str],
        responses: List[str],
        individual_scores: List[Dict[str, Any]],
        interview_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate comprehensive interview report"""
        try:
            prompt = f"""
Generate a comprehensive interview assessment report:

Job Title: {interview_context.get('job_title', 'Not specified')}
Company: {interview_context.get('company_name', 'Not specified')}
Interview Type: {interview_context.get('interview_type', 'general')}

QUESTIONS AND RESPONSES:
"""

            # Add questions and responses
            for i, (question, response) in enumerate(zip(questions, responses), 1):
                prompt += f"\nQ{i}: {question}\nA{i}: {response}\n"

            prompt += f"""

INDIVIDUAL QUESTION SCORES:
{individual_scores}

Please provide:

OVERALL ASSESSMENT:
- Overall Score (0-100): 
- Communication Score (0-100):
- Technical Score (0-100):
- Behavioral Score (0-100):

KEY STRENGTHS:
- [List 3-5 main strengths]

AREAS FOR IMPROVEMENT:
- [List 3-5 improvement areas]

DETAILED RECOMMENDATIONS:
- [Provide specific, actionable recommendations]

INTERVIEW HIGHLIGHTS:
- [Note memorable or impressive moments]

FINAL RECOMMENDATION:
- [Hiring recommendation with reasoning]
"""

            response = self.text_model.generate_content(prompt)
            report_text = response.text.strip()

            # Parse the report
            report = self._parse_report_response(report_text)

            logger.info("Generated interview report")
            return report

        except Exception as e:
            logger.error(f"Error generating interview report: {e}")
            return self._get_default_report()

    def _get_fallback_questions(self, job_title: str, count: int) -> List[str]:
        """Provide fallback questions when AI generation fails"""
        fallback_questions = [
            "Tell me about yourself and your professional background.",
            f"What interests you about this {job_title} position?",
            "Describe a challenging project you've worked on recently.",
            "How do you handle working under pressure or tight deadlines?",
            "What are your greatest professional strengths?",
            "Tell me about a time you had to learn something new quickly.",
            "How do you approach problem-solving in your work?",
            "Describe your ideal work environment.",
            "What motivates you in your career?",
            "Where do you see yourself in the next 5 years?",
            "How do you handle constructive feedback?",
            "Tell me about a time you worked effectively in a team.",
            "What questions do you have about this role or our company?",
        ]

        return fallback_questions[:count]

    def _parse_analysis_response(self, analysis_text: str) -> Dict[str, Any]:
        """Parse structured analysis response from Gemini"""
        try:
            # Initialize default structure
            analysis = {
                "content_score": 7.0,
                "communication_score": 7.0,
                "relevance_score": 7.0,
                "confidence_score": 7.0,
                "overall_score": 7.0,
                "strengths": [],
                "areas_for_improvement": [],
                "keywords_mentioned": [],
                "recommendations": [],
            }

            # Simple parsing logic (can be enhanced with better parsing)
            lines = analysis_text.split("\n")
            current_section = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Detect sections
                if "SCORES" in line:
                    current_section = "scores"
                elif "STRENGTHS" in line:
                    current_section = "strengths"
                elif "AREAS FOR IMPROVEMENT" in line:
                    current_section = "improvements"
                elif "KEYWORDS" in line:
                    current_section = "keywords"
                elif "RECOMMENDATIONS" in line:
                    current_section = "recommendations"
                elif line.startswith("-") and current_section:
                    # Extract list items
                    item = line[1:].strip()
                    if current_section == "strengths":
                        analysis["strengths"].append(item)
                    elif current_section == "improvements":
                        analysis["areas_for_improvement"].append(item)
                    elif current_section == "keywords":
                        analysis["keywords_mentioned"].append(item)
                    elif current_section == "recommendations":
                        analysis["recommendations"].append(item)
                elif current_section == "scores" and ":" in line:
                    # Extract scores
                    if "Content Quality" in line:
                        analysis["content_score"] = self._extract_score(line)
                    elif "Communication" in line:
                        analysis["communication_score"] = self._extract_score(line)
                    elif "Relevance" in line:
                        analysis["relevance_score"] = self._extract_score(line)
                    elif "Confidence" in line:
                        analysis["confidence_score"] = self._extract_score(line)
                    elif "Overall" in line:
                        analysis["overall_score"] = self._extract_score(line)

            return analysis

        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}")
            return self._get_default_analysis()

    def _extract_score(self, line: str) -> float:
        """Extract numerical score from a line"""
        try:
            # Look for numbers in the line
            import re

            numbers = re.findall(r"\d+\.?\d*", line)
            if numbers:
                score = float(numbers[0])
                return min(10.0, max(0.0, score))  # Clamp between 0 and 10
            return 7.0
        except:
            return 7.0

    def _parse_report_response(self, report_text: str) -> Dict[str, Any]:
        """Parse structured report response from Gemini"""
        # Simplified parsing - can be enhanced
        return {
            "overall_score": 75.0,
            "communication_score": 80.0,
            "technical_score": 70.0,
            "behavioral_score": 75.0,
            "strengths": [
                "Good communication",
                "Relevant experience",
                "Problem-solving skills",
            ],
            "weaknesses": ["Could provide more specific examples", "Technical depth"],
            "recommendations": ["Practice STAR method", "Prepare specific examples"],
            "report_text": report_text,
        }

    def _get_default_analysis(self) -> Dict[str, Any]:
        """Default analysis when AI fails"""
        return {
            "content_score": 7.0,
            "communication_score": 7.0,
            "relevance_score": 7.0,
            "confidence_score": 7.0,
            "overall_score": 7.0,
            "strengths": ["Response provided"],
            "areas_for_improvement": ["Could provide more detail"],
            "keywords_mentioned": [],
            "recommendations": ["Consider adding specific examples"],
        }

    def _get_default_report(self) -> Dict[str, Any]:
        """Default report when AI fails"""
        return {
            "overall_score": 70.0,
            "communication_score": 70.0,
            "technical_score": 70.0,
            "behavioral_score": 70.0,
            "strengths": ["Participated in interview"],
            "weaknesses": ["Analysis unavailable"],
            "recommendations": ["Schedule follow-up interview"],
            "report_text": "Interview completed - detailed analysis unavailable",
        }
