"""Regla operativa 3+1 / 2+1 para selecciones NBA congeladas.

Las tres predicciones originales NO se eliminan del archivo. Si la adicional
ofrecida y archivada coincide exactamente (mismo contrato, equipo y línea),
se excluye solo de la cartera activa Top 3 para no duplicar stake o acierto.
"""
from __future__ import annotations


def same_outcome(top: dict, additional: dict | None) -> bool:
    if not isinstance(additional, dict) or not isinstance(top, dict):
        return False
    contract = top.get("contract")
    return bool(
        top.get("event_id")
        and top.get("event_id") == additional.get("event_id")
        and isinstance(contract, dict) and contract
        and contract == additional.get("contract")
    )


def active_top3(picks: dict, real_extras: dict) -> dict:
    """Return a new mapping of active Top 3 positions; archive stays intact."""
    by_game = {
        row["event_id"]: row
        for row in real_extras.values()
        if isinstance(row, dict) and row.get("event_id")
    }
    return {
        key: row for key, row in picks.items()
        if not same_outcome(row, by_game.get(row.get("event_id")))
    }
