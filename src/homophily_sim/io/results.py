"""Write and restore a complete simulation run as JSON and Parquet."""

import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd  # type: ignore[import-untyped]

from homophily_sim.config import SimulationConfig
from homophily_sim.domain.agent import StudentAgent
from homophily_sim.domain.interaction import InteractionRecord
from homophily_sim.io.metadata import RunMetadata

_NESTED_AGENT_FIELDS = (
    "interests",
    "topic_orientations",
    "course_assignments",
    "section_assignments",
    "relationships",
)
_RELATIONSHIP_COLUMNS = ("observer_id", "other_id", "weight")


@dataclass(frozen=True)
class StoredRun:
    """Typed contents restored from one output directory."""

    config: SimulationConfig
    agents: list[StudentAgent]
    interactions: list[InteractionRecord]
    relationships: pd.DataFrame
    metadata: RunMetadata


def _agent_row(agent: StudentAgent) -> dict[str, object]:
    row: dict[str, object] = agent.model_dump(mode="json")
    for field in _NESTED_AGENT_FIELDS:
        value = row[field]
        if field == "interests":
            value = sorted(agent.interests)
        row[field] = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return row


def _relationship_rows(agents: list[StudentAgent]) -> list[dict[str, int | float]]:
    return [
        {"observer_id": agent.id, "other_id": other_id, "weight": weight}
        for agent in agents
        for other_id, weight in sorted(agent.relationships.items())
    ]


def _validate_run(
    config: SimulationConfig,
    agents: list[StudentAgent],
    interactions: list[InteractionRecord],
    metadata: RunMetadata,
) -> None:
    if metadata.scenario != config.scenario:
        raise ValueError("metadata scenario does not match configuration")
    ids = [agent.id for agent in agents]
    if len(ids) != config.population_size or len(set(ids)) != len(ids):
        raise ValueError("agents must contain the configured number of unique students")
    known_ids = set(ids)
    if any(
        other not in known_ids or other == agent.id
        for agent in agents
        for other in agent.relationships
    ):
        raise ValueError("relationships must reference another saved student")
    if any(
        record.run_id != metadata.run_id
        or record.seed != metadata.seed
        or record.sender_id not in known_ids
        or record.receiver_id not in known_ids
        for record in interactions
    ):
        raise ValueError("interactions must match the run and saved students")


def save_run(
    output_root: str | Path,
    *,
    config: SimulationConfig,
    agents: list[StudentAgent],
    interactions: list[InteractionRecord],
    metadata: RunMetadata,
) -> Path:
    """Write all five run artifacts, refusing to overwrite a previous run."""
    _validate_run(config, agents, interactions, metadata)
    root = Path(output_root)
    destination = root / metadata.run_id
    root.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)

    with TemporaryDirectory(prefix=".run-", dir=root) as temporary:
        stage = Path(temporary)
        (stage / "config.json").write_text(
            config.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        (stage / "run_metadata.json").write_text(
            metadata.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        pd.DataFrame([_agent_row(agent) for agent in agents]).to_parquet(
            stage / "agents.parquet", index=False
        )
        pd.DataFrame(
            [record.model_dump(mode="python") for record in interactions],
            columns=list(InteractionRecord.model_fields),
        ).to_parquet(stage / "interactions.parquet", index=False)
        pd.DataFrame(_relationship_rows(agents), columns=list(_RELATIONSHIP_COLUMNS)).to_parquet(
            stage / "relationships.parquet", index=False
        )
        stage.rename(destination)
    return destination


def load_run(path: str | Path) -> StoredRun:
    """Read the saved run, restoring agent containers and interaction times."""
    directory = Path(path)
    config = SimulationConfig.model_validate_json(
        (directory / "config.json").read_text(encoding="utf-8")
    )
    metadata = RunMetadata.model_validate_json(
        (directory / "run_metadata.json").read_text(encoding="utf-8")
    )
    agents = []
    for row in pd.read_parquet(directory / "agents.parquet").to_dict("records"):
        for field in _NESTED_AGENT_FIELDS:
            row[field] = json.loads(row[field])
        agents.append(StudentAgent.model_validate(row))

    interaction_rows = pd.read_parquet(directory / "interactions.parquet")
    if "participation_probability" in interaction_rows:
        probabilities = interaction_rows["participation_probability"].astype(object)
        interaction_rows["participation_probability"] = probabilities.where(
            probabilities.notna(), None
        )
    interactions = [
        InteractionRecord.model_validate(row) for row in interaction_rows.to_dict("records")
    ]
    relationships = pd.read_parquet(directory / "relationships.parquet")
    _validate_run(config, agents, interactions, metadata)
    expected = pd.DataFrame(_relationship_rows(agents), columns=list(_RELATIONSHIP_COLUMNS))
    if not relationships.equals(expected):
        raise ValueError("relationship table does not match saved agents")
    return StoredRun(config, agents, interactions, relationships, metadata)
