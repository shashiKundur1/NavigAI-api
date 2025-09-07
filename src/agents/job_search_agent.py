import instructor
import google.generativeai as genai
from models.job_search import StudentProfile, JobSearchQuery
from core.settings import Settings

genai.configure(api_key=Settings.GEMINI_API_KEY)

gemini_client = genai.GenerativeModel(model_name="gemini-1.5-flash")

client = instructor.from_gemini(gemini_client)


def generate_job_search_query(profile: StudentProfile) -> JobSearchQuery:
    """Generates a job search query from a student profile using an AI model."""

    all_skills = list(set(profile.current_skills + profile.target_skills))

    prompt = f"""
    Based on the following student profile, create a targeted job search query.
    The student is in their {profile.current_year} year, graduating in {profile.passed_out_year}.
    Their primary interest is in '{profile.interested_domain}'.
    They have skills in: {', '.join(profile.current_skills)}.
    They want to work with: {', '.join(profile.target_skills)}.

    Generate relevant job titles, keywords, and technology slugs.
    Focus on entry-level or internship roles.
    """

    try:
        query = client.create(
            response_model=JobSearchQuery,
            messages=[{"role": "user", "content": prompt}],
        )
        return query
    except Exception as e:
        print(f"Error generating AI query: {e}")
        return JobSearchQuery(
            job_title_or=[profile.interested_domain],
            job_description_contains_or=all_skills,
            job_technology_slug_or=all_skills,
        )
