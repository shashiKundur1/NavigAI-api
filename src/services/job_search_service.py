import httpx
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone

from models.job_search import StudentProfile, JobSearchQuery
from agents.job_search_agent import generate_job_search_query
from core.settings import THEIR_STACK_API_KEY
from db import firebase

THEIR_STACK_API_URL = "https://api.theirstack.com/v1/jobs/search"
API_TIMEOUT = 30.0
FIRESTORE_COLLECTION = "job_searches"


async def _save_search_to_firebase(
    profile: StudentProfile, query: JobSearchQuery, results: Dict[str, Any], userId: str
) -> None:
    """Saves the search profile, AI query, and job results to Firestore."""
    if not firebase.db:
        print("Firestore client not initialized. Skipping save.")
        return

    search_record = {
        "userId": userId,
        "student_profile": profile.model_dump(),
        "ai_query": query.model_dump(),
        "job_results": results,
        "created_at": datetime.now(timezone.utc),
    }

    await asyncio.to_thread(
        firebase.db.collection(FIRESTORE_COLLECTION).add, search_record
    )
    print(f"Successfully saved search and results for '{profile.name}' to Firestore.")


async def find_relevant_jobs(profile: StudentProfile, userId: str) -> Dict[str, Any]:
    """Orchestrates job searching and saves the request and results to Firebase."""

    ai_query = generate_job_search_query(profile)

    search_payload = {
        "order_by": [{"desc": True, "field": "date_posted"}],
        "limit": 25,
        "posted_at_max_age_days": 14,
        "job_country_code_or": ["IN"],
        **ai_query.model_dump(exclude_defaults=True),
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {THEIR_STACK_API_KEY}",
    }

    job_results = {}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                THEIR_STACK_API_URL,
                headers=headers,
                json=search_payload,
                timeout=API_TIMEOUT,
            )
            response.raise_for_status()
            job_results = response.json()
        except httpx.RequestError as e:
            job_results = {"error": f"API request failed: {e}"}
        except httpx.HTTPStatusError as e:
            job_results = {
                "error": f"API returned an error: {e.response.status_code}",
                "details": e.response.text,
            }

    await _save_search_to_firebase(profile, ai_query, job_results, userId)

    return job_results
