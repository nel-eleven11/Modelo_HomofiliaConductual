"""Mesa-managed weekly progression of the synthetic student cohort."""

from __future__ import annotations

from collections.abc import Sequence

import mesa  # type: ignore[import-untyped]

from homophily_sim.config import SimulationConfig
from homophily_sim.data.demographics import DemographicProfile
from homophily_sim.data.population import generate_population
from homophily_sim.data.topics import TopicBank
from homophily_sim.domain.agent import StudentAgent
from homophily_sim.domain.interaction import InteractionRecord
from homophily_sim.domain.section import Section
from homophily_sim.llm.base import LanguageModelProvider
from homophily_sim.network.metrics import NetworkMetrics, compute_metrics
from homophily_sim.network.snapshots import NetworkSnapshot, capture_snapshot
from homophily_sim.nlp.base import SentimentAnalyzer
from homophily_sim.simulation.calendar import SemesterSchedule, generate_academic_calendar
from homophily_sim.simulation.conversation import ConversationEvent, simulate_week
from homophily_sim.simulation.enrollment import enroll_semester


class StudentMesaAgent(mesa.Agent):  # type: ignore[misc]
    """Mesa registration and lifecycle around one validated student state."""

    def __init__(self, model: HomophilyModel, state: StudentAgent) -> None:
        super().__init__(model)
        self.state = state


class HomophilyModel(mesa.Model):  # type: ignore[misc]
    """Advance exactly one academic week per Mesa step, with seeded streams."""

    def __init__(
        self,
        config: SimulationConfig,
        bank: TopicBank,
        profile: DemographicProfile,
        *,
        run_seed: int,
        run_id: str,
        language_model: LanguageModelProvider,
        sentiment_analyzer: SentimentAnalyzer,
    ) -> None:
        super().__init__(rng=run_seed)
        self.config = config
        self.bank = bank
        self.run_seed = run_seed
        self.run_id = run_id
        self.language_model = language_model
        self.sentiment_analyzer = sentiment_analyzer
        self.calendar = generate_academic_calendar(config, run_seed)
        for state in generate_population(config, bank, profile, run_seed):
            StudentMesaAgent(self, state)
        self.current_semester = 0
        self.current_week = 0
        self.sections_by_course: dict[str, tuple[Section, ...]] = {}
        self.last_events: list[ConversationEvent] = []
        self.conversation_count = 0
        self.interactions: list[InteractionRecord] = []
        self.snapshots: list[NetworkSnapshot] = []
        self.year_snapshots: list[NetworkSnapshot] = []
        self.final_snapshot: NetworkSnapshot | None = None
        self.metric_history: list[tuple[int, NetworkMetrics]] = []
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "semester": "current_semester",
                "week": "current_week",
                "conversations": "conversation_count",
                "interactions": lambda model: len(model.interactions),
            }
        )

    @property
    def students(self) -> list[StudentAgent]:
        """Return domain states in stable student-id order from Mesa's registry."""
        return sorted(
            (agent.state for agent in self.agents if isinstance(agent, StudentMesaAgent)),
            key=lambda state: state.id,
        )

    def _finish_semester(self, students: Sequence[StudentAgent]) -> None:
        semester = self.current_semester
        snapshot = capture_snapshot(
            students,
            self.interactions,
            kind="semester_end",
            semester=semester,
            total_semesters=self.config.semesters,
        )
        self.snapshots.append(snapshot)
        self.metric_history.append(
            (semester, compute_metrics(snapshot.graph, students, self.config))
        )
        if semester % 2 == 0:
            self.year_snapshots.append(
                capture_snapshot(
                    students,
                    self.interactions,
                    kind="year_end",
                    semester=semester,
                    total_semesters=self.config.semesters,
                )
            )
        if semester == self.config.semesters:
            self.final_snapshot = capture_snapshot(
                students,
                self.interactions,
                kind="final",
                semester=semester,
                total_semesters=self.config.semesters,
            )
            self.running = False

    def step(self) -> None:
        """Execute all section conversations for the next academic week."""
        if not self.running:
            return
        index = self.steps - 1  # Mesa increments steps before invoking this method.
        self.current_semester, week_index = divmod(index, self.config.weeks_per_semester)
        self.current_semester += 1
        self.current_week = week_index + 1
        schedule: SemesterSchedule = self.calendar[self.current_semester - 1]
        students = self.students
        if self.current_week == 1:
            self.sections_by_course = enroll_semester(
                students, schedule, self.config, self.run_seed
            )
        self.last_events = simulate_week(
            students,
            schedule,
            self.sections_by_course,
            self.bank,
            self.config,
            self.run_seed,
            self.current_week,
            self.run_id,
            self.language_model,
            self.sentiment_analyzer,
        )
        self.conversation_count += len(self.last_events)
        self.interactions.extend(record for event in self.last_events for record in event.records)
        self.datacollector.collect(self)
        if self.current_week == self.config.weeks_per_semester:
            self._finish_semester(students)

    def run_to_completion(self) -> None:
        """Run the remaining weeks using Mesa's step clock."""
        while self.running:
            self.step()
