"""A course section and its assigned student IDs."""

from typing import Self

from pydantic import BaseModel, Field, model_validator


class Section(BaseModel):
    course_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    student_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_students(self) -> Self:
        if len(self.student_ids) != len(set(self.student_ids)):
            raise ValueError("student IDs in a section must be unique")
        return self
