"""Student state; relationship direction is always observer to other student."""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Sex(StrEnum):
    FEMALE = "FEMALE"
    MALE = "MALE"


class Origin(StrEnum):
    GUATEMALA_DEPARTMENT = "GUATEMALA_DEPARTMENT"
    REST_OF_COUNTRY = "REST_OF_COUNTRY"


class StudentAgent(BaseModel):
    """One synthetic student in the longitudinal cohort."""

    id: int = Field(ge=0)
    age: int = Field(ge=0)
    sex: Sex
    origin: Origin
    semester: int = Field(ge=1, le=10)
    interests: set[str] = Field(min_length=1, max_length=5)
    extraversion: float = Field(ge=0, le=10)
    topic_orientations: dict[str, float] = Field(default_factory=dict)
    course_assignments: dict[int, list[str]] = Field(default_factory=dict)
    section_assignments: dict[int, dict[str, str]] = Field(default_factory=dict)
    relationships: dict[int, float] = Field(default_factory=dict)

    @field_validator("topic_orientations")
    @classmethod
    def valid_orientations(cls, values: dict[str, float]) -> dict[str, float]:
        if any(not -1 <= value <= 1 for value in values.values()):
            raise ValueError("topic orientations must be in [-1, 1]")
        return values

    @field_validator("relationships")
    @classmethod
    def valid_relationships(cls, values: dict[int, float]) -> dict[int, float]:
        if any(not 0 <= value <= 1 for value in values.values()):
            raise ValueError("relationships must be in [0, 1]")
        return values

    def relationship_to(self, other_id: int, initial: float = 0.5) -> float:
        """Return observer's directed bond, including the neutral prior."""
        if not 0 <= initial <= 1:
            raise ValueError("initial relationship must be in [0, 1]")
        return self.relationships.get(other_id, initial)
