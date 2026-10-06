"""combat: a small deterministic turn based combat kernel."""

from .core import (
    MIN_DAMAGE,
    SHIELD_RATIO,
    Combat,
    Combatant,
    DotEffect,
    armor_multiplier,
    clamp,
    resist_multiplier,
)

__all__ = [
    "MIN_DAMAGE",
    "SHIELD_RATIO",
    "Combat",
    "Combatant",
    "DotEffect",
    "armor_multiplier",
    "clamp",
    "resist_multiplier",
]
