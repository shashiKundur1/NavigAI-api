import asyncio
from datetime import datetime, timezone
from collections import Counter
import re

from db import firebase
from agents.roadmap_agent import generate_roadmap

FIRESTORE_SEARCHES = "job_searches"
FIRESTORE_ROADMAPS = "roadmaps"


def _extract_skills_from_searches(search_docs: list) -> list:
    """Analyzes job descriptions to find the most common skills."""
    all_text = ""
    for doc in search_docs:
        if "job_results" in doc and isinstance(doc["job_results"], dict):
            if "results" in doc["job_results"] and isinstance(
                doc["job_results"]["results"], list
            ):
                for job in doc["job_results"]["results"]:
                    if job and "description" in job and job["description"]:
                        all_text += job["description"].lower()

    skills = re.findall(
        r"\b(python|java|react|node.js|typescript|aws|docker|kubernetes|sql|gcp|azure|fastapi|flask|git)\b",
        all_text,
    )

    return [skill for skill, count in Counter(skills).most_common(10)]


async def generate_student_roadmap(user_id: str) -> str:
    """Orchestrates the creation of a student's learning roadmap."""
    if not firebase.db:
        raise ConnectionError("Firestore client not initialized.")

    def fetch_data():
        docs_query = (
            firebase.db.collection(FIRESTORE_SEARCHES)
            .where("userId", "==", user_id)
            .stream()
        )
        return [doc.to_dict() for doc in docs_query]

    search_docs = await asyncio.to_thread(fetch_data)

    if not search_docs:
        return "<h2>No Data Found</h2><p>Please perform a few job searches first to generate a roadmap.</p>"

    top_skills = _extract_skills_from_searches(search_docs)
    grad_year = search_docs[0]["student_profile"]["passed_out_year"]

    roadmap_result = generate_roadmap(top_skills, grad_year)
    roadmap_html = roadmap_result.roadmap_html

    def save_roadmap():
        roadmap_record = {
            "userId": user_id,
            "roadmap_html": roadmap_html,
            "created_at": datetime.now(timezone.utc),
            "based_on_skills": top_skills,
        }

        firebase.db.collection(FIRESTORE_ROADMAPS).document(user_id).set(
            roadmap_record, merge=True
        )

    await asyncio.to_thread(save_roadmap)

    return roadmap_html
