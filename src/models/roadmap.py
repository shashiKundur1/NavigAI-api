from pydantic import BaseModel, Field


class RoadmapRequest(BaseModel):
    """The input request to generate a roadmap, needs a user identifier."""

    user_id: str = Field(
        description="The unique ID of the user, e.g., Firebase Auth UID."
    )


class GeneratedRoadmap(BaseModel):
    """The structured output from the AI agent, containing the HTML roadmap."""

    roadmap_html: str = Field(
        description="A clean, well-formatted HTML string for the student's roadmap."
    )
