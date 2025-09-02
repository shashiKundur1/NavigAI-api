import os
from pathlib import Path
import tempfile
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from scipy import stats
from typing import Dict, Any, List, Optional
from datetime import datetime

from models.mock_interview import (
    InterviewSession,
    Question,
    Answer,
    InterviewReport,
    PerformanceMetrics,
)
from db.firebase_db import save_interview_report

import logging

logger = logging.getLogger(__name__)


class ReportGenerationService:
    def __init__(self):
        pass

    def generate_interview_report(self, session: InterviewSession) -> Optional[str]:
        """Generate comprehensive PDF report"""
        performance_metrics = PerformanceMetrics()
        if session.performance_metrics:
            performance_metrics = PerformanceMetrics(**session.performance_metrics)

        # Create report
        report = InterviewReport(
            session_id=session.id,
            candidate_id=session.candidate_id,
            job_title=session.job_title,
            performance_metrics=performance_metrics,
            detailed_analysis=self._generate_detailed_analysis(session),
            question_responses=self._generate_question_responses(session),
            improvement_suggestions=performance_metrics.recommendations,
        )

        # Generate PDF
        pdf_path = self._create_pdf_report(report)

        # Save report to Firebase
        save_interview_report(report.dict())

        return pdf_path

    def _generate_detailed_analysis(self, session: InterviewSession) -> Dict[str, Any]:
        """Generate detailed analysis of the interview"""
        analysis = {
            "total_questions": len(session.questions_asked),
            "total_answers": len(session.answers),
            "average_response_time": (
                np.mean([answer.audio_duration for answer in session.answers])
                if session.answers
                else 0
            ),
            "performance_trend": self._calculate_performance_trend(session),
            "question_type_breakdown": self._analyze_question_type_performance(session),
            "keyword_coverage": self._analyze_keyword_coverage(session),
            "response_quality_progression": self._analyze_response_quality_progression(
                session
            ),
            "emotional_consistency": self._analyze_emotional_consistency(session),
            "communication_effectiveness": self._analyze_communication_effectiveness(
                session
            ),
        }
        return analysis

    def _calculate_performance_trend(self, session: InterviewSession) -> str:
        """Calculate performance trend over the interview"""
        if len(session.answers) < 3:
            return "Insufficient data"

        scores = [answer.technical_score for answer in session.answers]
        trend = stats.linregress(range(len(scores)), scores)

        if trend.slope > 0.05:
            return "Improving"
        elif trend.slope < -0.05:
            return "Declining"
        else:
            return "Stable"

    def _analyze_question_type_performance(
        self, session: InterviewSession
    ) -> Dict[str, float]:
        """Analyze performance by question type"""
        type_performance = {}

        for answer in session.answers:
            # Find the question for this answer
            question = None
            for q_id in session.questions_asked:
                if q_id == answer.question_id:
                    question = q_id
                    break

            if question:
                if question not in type_performance:
                    type_performance[question] = []
                type_performance[question].append(answer.technical_score)

        # Calculate averages
        return {q_type: np.mean(scores) for q_type, scores in type_performance.items()}

    def _analyze_keyword_coverage(self, session: InterviewSession) -> Dict[str, Any]:
        """Analyze how well the candidate covered expected keywords"""
        keyword_coverage = {}

        for answer in session.answers:
            # Find the question for this answer
            question = None
            for q_id in session.questions_asked:
                if q_id == answer.question_id:
                    question = q_id
                    break

            if question and hasattr(question, "expected_keywords"):
                # Check which keywords were mentioned in the answer
                mentioned_keywords = []
                for keyword in question.expected_keywords:
                    if keyword.lower() in answer.text.lower():
                        mentioned_keywords.append(keyword)

                coverage_rate = (
                    len(mentioned_keywords) / len(question.expected_keywords)
                    if question.expected_keywords
                    else 0
                )

                keyword_coverage[question.id] = {
                    "expected_keywords": question.expected_keywords,
                    "mentioned_keywords": mentioned_keywords,
                    "coverage_rate": coverage_rate,
                }

        return keyword_coverage

    def _analyze_response_quality_progression(
        self, session: InterviewSession
    ) -> Dict[str, Any]:
        """Analyze how response quality progressed throughout the interview"""
        if not session.answers:
            return {"progression": "No data"}

        # Calculate scores for each answer
        scores = []
        for answer in session.answers:
            # Calculate a composite score
            composite_score = (
                answer.technical_score * 0.4
                + answer.fluency_score * 0.2
                + answer.confidence_score * 0.2
                + answer.sentiment_score * 0.2
            )
            scores.append(composite_score)

        # Determine progression
        if len(scores) < 3:
            return {"progression": "Insufficient data"}

        # Calculate trend
        x = list(range(len(scores)))
        slope, _, _, _, _ = stats.linregress(x, scores)

        if slope > 0.05:
            progression = "Improving"
        elif slope < -0.05:
            progression = "Declining"
        else:
            progression = "Stable"

        return {"progression": progression, "slope": slope, "scores": scores}

    def _analyze_emotional_consistency(
        self, session: InterviewSession
    ) -> Dict[str, Any]:
        """Analyze emotional consistency throughout the interview"""
        if not session.answers:
            return {"consistency": "No data"}

        # Extract emotion scores
        emotion_scores = []
        for answer in session.answers:
            if answer.emotion_scores:
                # Get the dominant emotion for each answer
                dominant_emotion = max(
                    answer.emotion_scores.items(), key=lambda x: x[1]
                )
                emotion_scores.append(dominant_emotion[0])

        # Calculate consistency (how often the same emotion is dominant)
        if len(emotion_scores) < 2:
            return {"consistency": "Insufficient data"}

        most_common_emotion = max(set(emotion_scores), key=emotion_scores.count)
        consistency_rate = emotion_scores.count(most_common_emotion) / len(
            emotion_scores
        )

        return {
            "consistency": consistency_rate,
            "most_common_emotion": most_common_emotion,
            "emotion_distribution": {
                emotion: emotion_scores.count(emotion) / len(emotion_scores)
                for emotion in set(emotion_scores)
            },
        }

    def _analyze_communication_effectiveness(
        self, session: InterviewSession
    ) -> Dict[str, Any]:
        """Analyze communication effectiveness throughout the interview"""
        if not session.answers:
            return {"effectiveness": "No data"}

        # Calculate communication scores
        communication_scores = []
        for answer in session.answers:
            # Calculate a communication effectiveness score
            effectiveness = (
                answer.fluency_score * 0.4
                + answer.confidence_score * 0.3
                + (answer.sentiment_score + 1) / 2 * 0.3  # Convert from [-1,1] to [0,1]
            )
            communication_scores.append(effectiveness)

        # Calculate average and trend
        avg_effectiveness = np.mean(communication_scores)

        if len(communication_scores) >= 3:
            x = list(range(len(communication_scores)))
            slope, _, _, _, _ = stats.linregress(x, communication_scores)

            if slope > 0.05:
                trend = "Improving"
            elif slope < -0.05:
                trend = "Declining"
            else:
                trend = "Stable"
        else:
            trend = "Insufficient data"

        return {
            "average_effectiveness": avg_effectiveness,
            "trend": trend,
            "scores": communication_scores,
        }

    def _generate_question_responses(
        self, session: InterviewSession
    ) -> List[Dict[str, Any]]:
        """Generate detailed question-response analysis"""
        responses = []

        for answer in session.answers:
            # Find the question for this answer
            question = None
            for q_id in session.questions_asked:
                if q_id == answer.question_id:
                    question = q_id
                    break

            if question:
                response = {
                    "question": question,
                    "question_type": "Unknown",
                    "difficulty": "Intermediate",
                    "response": answer.text,
                    "score": answer.technical_score,
                    "feedback": self._generate_question_feedback(answer),
                }
                responses.append(response)

        return responses

    def _generate_question_feedback(self, answer: Answer) -> str:
        """Generate feedback for a specific question"""
        if answer.technical_score >= 0.8:
            return "Excellent response! You demonstrated strong understanding."
        elif answer.technical_score >= 0.6:
            return "Good response with room for improvement."
        else:
            return "Consider reviewing this topic and practicing similar questions."

    def _create_pdf_report(self, report: InterviewReport) -> str:
        """Create PDF report using ReportLab and save to Downloads folder"""
        # Get user's Downloads folder
        downloads_folder = Path.home() / "Downloads"

        # Ensure Downloads folder exists
        downloads_folder.mkdir(parents=True, exist_ok=True)

        # Create file path with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = downloads_folder / f"interview_report_{timestamp}.pdf"

        # Create PDF document
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        story = []

        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue,
        )

        # Add title
        title = Paragraph("AI Mock Interview Report", title_style)
        story.append(title)

        # Add session info
        session_info = [
            ["Candidate ID", report.candidate_id],
            ["Job Title", report.job_title],
            ["Session ID", report.session_id],
            ["Generated", report.generated_at.strftime("%Y-%m-%d %H:%M:%S")],
        ]

        session_table = Table(session_info, colWidths=[2 * inch, 4 * inch])
        session_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(session_table)
        story.append(Spacer(1, 20))

        # Add performance metrics
        metrics = report.performance_metrics
        metrics_data = [
            ["Metric", "Score", "Assessment"],
            [
                "Technical Skills",
                f"{metrics.technical_score:.2f}",
                self._score_to_grade(metrics.technical_score),
            ],
            [
                "Communication",
                f"{metrics.communication_score:.2f}",
                self._score_to_grade(metrics.communication_score),
            ],
            [
                "Emotional Intelligence",
                f"{metrics.emotional_intelligence_score:.2f}",
                self._score_to_grade(metrics.emotional_intelligence_score),
            ],
            [
                "Behavioral",
                f"{metrics.behavioral_score:.2f}",
                self._score_to_grade(metrics.behavioral_score),
            ],
            [
                "Overall",
                f"{metrics.overall_score:.2f}",
                self._score_to_grade(metrics.overall_score),
            ],
        ]

        metrics_table = Table(metrics_data, colWidths=[2 * inch, 1 * inch, 2 * inch])
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(Paragraph("Performance Metrics", styles["Heading2"]))
        story.append(metrics_table)
        story.append(Spacer(1, 20))

        # Add performance chart
        chart_path = self._create_performance_chart(metrics)
        if chart_path:
            story.append(Image(chart_path, width=6 * inch, height=3 * inch))
            story.append(Spacer(1, 20))

        # Add detailed analysis
        story.append(Paragraph("Detailed Analysis", styles["Heading2"]))

        # Performance trend
        trend = report.detailed_analysis.get("performance_trend", "N/A")
        story.append(Paragraph(f"Performance Trend: {trend}", styles["Normal"]))
        story.append(Spacer(1, 10))

        # Response quality progression
        response_quality = report.detailed_analysis.get(
            "response_quality_progression", {}
        )
        if "progression" in response_quality:
            story.append(
                Paragraph(
                    f"Response Quality: {response_quality['progression']}",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 10))

        # Emotional consistency
        emotional_consistency = report.detailed_analysis.get(
            "emotional_consistency", {}
        )
        if "consistency" in emotional_consistency:
            consistency_pct = emotional_consistency["consistency"] * 100
            story.append(
                Paragraph(
                    f"Emotional Consistency: {consistency_pct:.1f}%", styles["Normal"]
                )
            )
            story.append(Spacer(1, 10))

        # Communication effectiveness
        comm_effectiveness = report.detailed_analysis.get(
            "communication_effectiveness", {}
        )
        if "average_effectiveness" in comm_effectiveness:
            effectiveness_pct = comm_effectiveness["average_effectiveness"] * 100
            story.append(
                Paragraph(
                    f"Communication Effectiveness: {effectiveness_pct:.1f}%",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 10))

        story.append(Spacer(1, 20))

        # Add strengths and weaknesses
        story.append(Paragraph("Strengths", styles["Heading2"]))
        for strength in metrics.strengths:
            story.append(Paragraph(f"• {strength}", styles["Normal"]))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Areas for Improvement", styles["Heading2"]))
        for weakness in metrics.weaknesses:
            story.append(Paragraph(f"• {weakness}", styles["Normal"]))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Recommendations", styles["Heading2"]))
        for recommendation in metrics.recommendations:
            story.append(Paragraph(f"• {recommendation}", styles["Normal"]))

        # Build PDF
        doc.build(story)

        # Clean up chart file
        if chart_path and os.path.exists(chart_path):
            os.remove(chart_path)

        return str(pdf_path)

    def _score_to_grade(self, score: float) -> str:
        """Convert score to grade"""
        if score >= 0.9:
            return "Excellent"
        elif score >= 0.8:
            return "Very Good"
        elif score >= 0.7:
            return "Good"
        elif score >= 0.6:
            return "Fair"
        else:
            return "Needs Improvement"

    def _create_performance_chart(self, metrics: PerformanceMetrics) -> Optional[str]:
        """Create performance chart"""
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=(8, 4))

            # Data
            categories = [
                "Technical",
                "Communication",
                "Emotional\nIntelligence",
                "Behavioral",
                "Overall",
            ]
            scores = [
                metrics.technical_score,
                metrics.communication_score,
                metrics.emotional_intelligence_score,
                metrics.behavioral_score,
                metrics.overall_score,
            ]

            # Create bar chart
            bars = ax.bar(
                categories,
                scores,
                color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
            )

            # Customize chart
            ax.set_ylim(0, 1)
            ax.set_ylabel("Score")
            ax.set_title("Performance Metrics")

            # Add value labels on bars
            for bar, score in zip(bars, scores):
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + 0.01,
                    f"{score:.2f}",
                    ha="center",
                    va="bottom",
                )

            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            plt.tight_layout()
            plt.savefig(temp_file.name, dpi=150, bbox_inches="tight")
            plt.close()

            return temp_file.name

        except Exception as e:
            logger.error(f"Chart creation error: {e}")
            return None
