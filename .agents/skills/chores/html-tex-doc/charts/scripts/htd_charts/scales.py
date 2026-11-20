"""Coordinate scales and tick formatting."""
from __future__ import annotations


class LinearScale:
    """Affine mapping from data domain [dmin, dmax] to SVG pixel range [r0, r1]."""

    def __init__(self, dmin: float, dmax: float, r0: float, r1: float) -> None:
        self.dmin = float(dmin)
        self.dmax = float(dmax)
        self.r0 = float(r0)
        self.r1 = float(r1)

    def map(self, value: float) -> float:
        span = self.dmax - self.dmin
        t = (float(value) - self.dmin) / span if span != 0 else 0.5
        return self.r0 + t * (self.r1 - self.r0)


def fmt_tick(value: float) -> str:
    """Format numeric axis tick without floating-point noise."""
    if abs(value) < 1e-11:
        return "0"
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.4f}".rstrip("0").rstrip(".")
