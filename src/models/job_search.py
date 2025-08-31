from pydantic import BaseModel, Field
from typing import List


class StudentProfile(BaseModel):
    """Represents the input profile of a student."""

    name: str
    college_name: str
    current_year: int
    passed_out_year: int
    current_skills: List[str]
    target_skills: List[str]
    interested_domain: str


class JobSearchQuery(BaseModel):
    """Defines the structured query for the TheirStack job search API."""

    job_title_or: List[str] = Field(
        default=[],
        description='A list of potential job titles to search for, like "Software Engineer" or "Data Analyst".',
    )
    job_description_contains_or: List[str] = Field(
        default=[], description="Keywords that should appear in the job description."
    )
    job_technology_slug_or: List[str] = Field(
        default=[],
        description='A list of technology slugs (e.g., "python", "reactjs") relevant to the job.',
    )
    job_seniority_or: List[str] = Field(
        default=["entry-level", "internship"],
        description="Seniority levels to target, defaults to entry-level roles.",
    )
