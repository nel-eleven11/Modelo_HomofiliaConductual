"""Comprobación mínima de la instalación del paquete."""

import importlib.util


def test_package_is_importable() -> None:
    """La instalación debe exponer homophily_sim sin ajustar PYTHONPATH."""
    assert importlib.util.find_spec("homophily_sim") is not None
    package = __import__("homophily_sim")
    assert package.__doc__
