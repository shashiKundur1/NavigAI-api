import asyncio
from datetime import datetime, timezone

from db import firebase
from agents.roadmap_agent import generate_roadmap
from google.cloud.firestore_v1.base_query import FieldFilter

FIRESTORE_SEARCHES = "job_searches"
FIRESTORE_ROADMAPS = "roadmaps"


async def generate_student_roadmap(user_id: str) -> str:
    """Orchestrates the creation of a student's learning roadmap."""
    if not firebase.db:
        raise ConnectionError("Firestore client not initialized.")

    def fetch_data():
        docs_query = (
            firebase.db.collection(FIRESTORE_SEARCHES)
            .where(filter=FieldFilter("userId", "==", user_id))
            .stream()
        )
        return [doc.to_dict() for doc in docs_query]

    search_docs = await asyncio.to_thread(fetch_data)

    if not search_docs:
        return "<h2>No Data Found</h2><p>Please perform a few job searches first to generate a roadmap.</p>"

    jobs_data = []
    for doc in search_docs:
        if "job_results" in doc and isinstance(doc["job_results"], dict):
            if "data" in doc["job_results"] and isinstance(
                doc["job_results"]["data"], list
            ):
                for job in doc["job_results"]["data"]:
                    if job and job.get("description") and job.get("job_title"):
                        jobs_data.append(
                            {
                                "title": job["job_title"],  # Correct field name
                                "description": job["description"],
                                "company": job.get("company", ""),
                                "technologies": job.get("technology_slugs", []),
                                "seniority": job.get("seniority", ""),
                            }
                        )

    if not jobs_data:
        return "<h2>Not Enough Job Data</h2><p>The job searches found did not contain enough information to generate a roadmap.</p>"

    # Get graduation year from student profile
    grad_year = None
    if search_docs and "student_profile" in search_docs[0]:
        grad_year = search_docs[0]["student_profile"].get("passed_out_year")

    if not grad_year:
        grad_year = datetime.now().year + 1

    roadmap_result = generate_roadmap(jobs_data, grad_year)
    roadmap_html = roadmap_result.roadmap_html

    def save_roadmap():
        roadmap_record = {
            "userId": user_id,
            "roadmap_html": roadmap_html,
            "created_at": datetime.now(timezone.utc),
            "based_on_job_count": len(jobs_data),
        }
        firebase.db.collection(FIRESTORE_ROADMAPS).document(user_id).set(
            roadmap_record, merge=True
        )

    await asyncio.to_thread(save_roadmap)

    return roadmap_html
