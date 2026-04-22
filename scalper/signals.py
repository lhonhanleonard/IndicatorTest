"""Combine individual signal scores into a weighted decision."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Decision:
    action: str                # LONG | SHORT | FLAT
    score: float               # weighted sum of component scores
    confidence: str            # low | medium | high
    components: dict[str, float] = field(default_factory=dict)
    price: float = 0.0
    stop: float = 0.0
    target: float = 0.0
    notes: list[str] = field(default_factory=list)


def combine(
    components: dict[str, float],
    weights: dict[str, float],
    enter: float = 1.5,
    strong: float = 3.0,
) -> tuple[str, float, str]:
    score = sum(components.get(name, 0.0) * weights.get(name, 0.0) for name in weights)
    abs_s = abs(score)
    if abs_s < enter:
        return "FLAT", score, "low"
    action = "LONG" if score > 0 else "SHORT"
    confidence = "high" if abs_s >= strong else "medium"
    return action, score, confidence


def build_decision(
    components: dict[str, float],
    weights: dict[str, float],
    price: float,
    atr_value: float,
    enter: float,
    strong: float,
    stop_mult: float,
    target_mult: float,
    notes: list[str] | None = None,
) -> Decision:
    action, score, confidence = combine(components, weights, enter, strong)
    if action == "LONG":
        stop = price - stop_mult * atr_value
        target = price + target_mult * atr_value
    elif action == "SHORT":
        stop = price + stop_mult * atr_value
        target = price - target_mult * atr_value
    else:
        stop = target = 0.0
    return Decision(
        action=action,
        score=round(score, 3),
        confidence=confidence,
        components={k: round(v, 3) for k, v in components.items()},
        price=price,
        stop=round(stop, 2),
        target=round(target, 2),
        notes=notes or [],
    )
