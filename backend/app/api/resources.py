"""Read-only resource endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.simulation.engine import engine

router = APIRouter(tags=["resources"])


@router.get("/ambulances")
def list_ambulances() -> list[dict[str, Any]]:
    return [a.model_dump() for a in engine.state.ambulances.values()]


@router.get("/hospitals")
def list_hospitals() -> list[dict[str, Any]]:
    return [h.model_dump() for h in engine.state.hospitals.values()]


@router.get("/shelters")
def list_shelters() -> list[dict[str, Any]]:
    return [s.model_dump() for s in engine.state.shelters.values()]
