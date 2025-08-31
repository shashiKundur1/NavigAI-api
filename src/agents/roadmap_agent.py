# src/agents/roadmap_agent.py

import instructor
import google.generativeai as genai
from typing import List
from models.roadmap import GeneratedRoadmap
from core.settings import GEMINI_API_KEY

# Configure and patch the Gemini client
genai.configure(api_key=GEMINI_API_KEY)
client = instructor.from_gemini(genai.GenerativeModel(model_name="gemini-1.5-flash"))


def generate_roadmap(top_skills: List[str], graduation_year: int) -> GeneratedRoadmap:
    """Generates a personalized learning roadmap for a student."""

    # Simple logic to determine the timeline
    from datetime import datetime

    current_year = datetime.now().year
    years_left = graduation_year - current_year
    timeline_desc = f"{years_left} years left until graduation in {graduation_year}."

    prompt = f"""
    You are an expert career coach AI. Your task is to create a personalized learning roadmap
    for a student based on skills required in jobs they are interested in.

    Student's Timeline: {timeline_desc}
    Top 5-10 In-Demand Skills Found In Job Postings: {', '.join(top_skills)}

    Create a structured, timeline-based learning roadmap. The output MUST be a single,
    clean, well-formatted HTML string. Use semantic tags like <h2>, <h3>, <h4>, <ul>, <li>,
    and <strong>. Do NOT include <html>, <head>, or <body> tags.

    Structure the roadmap by semesters or years. For each period, suggest 2-3 key skills
    to learn, practical project ideas, and career tips like networking or open-source
    contributions. Make it inspiring and actionable.
    """

    try:
        roadmap = client.create(
            response_model=GeneratedRoadmap,
            messages=[{"role": "user", "content": prompt}],
        )
        return roadmap
    except Exception as e:
        print(f"Error generating roadmap: {e}")
        return GeneratedRoadmap(
            roadmap_html="<h2>Error</h2><p>Could not generate roadmap at this time.</p>"
        )
