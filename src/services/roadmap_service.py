from datetime import datetime, timezone

from db import get_job_searches_by_user, save_roadmap
from agents.roadmap_agent import generate_roadmap


async def generate_student_roadmap(user_id: str) -> str:
    search_docs = await get_job_searches_by_user(user_id)

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
                                "title": job["job_title"],
                                "description": job["description"],
                                "company": job.get("company", ""),
                                "technologies": job.get("technology_slugs", []),
                                "seniority": job.get("seniority", ""),
                            }
                        )

    if not jobs_data:
        return "<h2>Not Enough Job Data</h2><p>The job searches found did not contain enough information to generate a roadmap.</p>"

    grad_year = None
    if search_docs and "student_profile" in search_docs[0]:
        grad_year = search_docs[0]["student_profile"].get("passed_out_year")

    if not grad_year:
        grad_year = datetime.now().year + 1

    roadmap_result = generate_roadmap(jobs_data, grad_year)
    roadmap_html = roadmap_result.roadmap_html

    roadmap_record = {
        "user_id": user_id,
        "roadmap_html": roadmap_html,
        "created_at": datetime.now(timezone.utc),
        "based_on_job_count": len(jobs_data),
    }
    await save_roadmap(user_id, roadmap_record)

    return roadmap_html
