"""Academic course identity for one semester."""

from pydantic import BaseModel, Field


class Course(BaseModel):
    course_id: str = Field(min_length=1)
    semester: int = Field(ge=1, le=10)
