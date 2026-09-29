"""Time series and final directed-relationship distribution figures."""

from collections.abc import Sequence
from pathlib import Path

from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from homophily_sim.network.metrics import NetworkMetrics

MetricSeries = Sequence[tuple[int, NetworkMetrics]]


def _figure() -> tuple[Figure, Axes]:
    figure = Figure(figsize=(8, 4.5), dpi=150)
    FigureCanvasAgg(figure)
    return figure, figure.subplots()


def plot_metric_trends(series: MetricSeries, output_dir: str | Path) -> tuple[Path, Path, Path]:
    """Draw density, two assortativities and modularity by semester."""
    if not series or len({semester for semester, _ in series}) != len(series):
        raise ValueError("metric series needs distinct semesters")
    ordered = sorted(series, key=lambda pair: pair[0])
    semesters = [semester for semester, _ in ordered]
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    figure, axes = _figure()
    axes.plot(semesters, [item.density for _, item in ordered], marker="o", color="#397da5")
    axes.set(title="Densidad de la red", xlabel="Semestre", ylabel="Densidad", ylim=(0, 1))
    axes.set_xticks(semesters)
    axes.grid(alpha=0.2)
    figure.tight_layout()
    density_path = root / "density_over_time.png"
    figure.savefig(density_path)

    figure, axes = _figure()
    for label, values, color in (
        ("Sexo", [item.sex_assortativity for _, item in ordered], "#d65a75"),
        ("Procedencia", [item.origin_assortativity for _, item in ordered], "#397da5"),
    ):
        axes.plot(
            semesters,
            [float("nan") if value is None else value for value in values],
            marker="o",
            label=label,
            color=color,
        )
    axes.set(
        title="Assortatividad por atributo", xlabel="Semestre", ylabel="Coeficiente", ylim=(-1, 1)
    )
    axes.set_xticks(semesters)
    axes.grid(alpha=0.2)
    axes.legend(frameon=False)
    figure.tight_layout()
    assortativity_path = root / "assortativity_over_time.png"
    figure.savefig(assortativity_path)

    figure, axes = _figure()
    axes.plot(semesters, [item.modularity for _, item in ordered], marker="o", color="#7651a8")
    axes.set(
        title="Modularidad de la proyección no dirigida", xlabel="Semestre", ylabel="Modularidad"
    )
    axes.set_xticks(semesters)
    axes.grid(alpha=0.2)
    figure.tight_layout()
    modularity_path = root / "modularity_over_time.png"
    figure.savefig(modularity_path)
    return density_path, assortativity_path, modularity_path


def plot_relationship_distribution(metrics: NetworkMetrics, destination: str | Path) -> Path:
    """Histogram of explicit final directed relationship weights."""
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = _figure()
    axes.hist(
        metrics.relationship_weights, bins=20, range=(0, 1), color="#397da5", edgecolor="white"
    )
    axes.set(
        title="Distribución de vínculos dirigidos",
        xlabel="Peso del vínculo R_ij",
        ylabel="Número de aristas",
        xlim=(0, 1),
    )
    axes.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(output)
    return output
