#!/usr/bin/env python3
"""Deterministic simulation script skeleton producing sim_data.json."""
from __future__ import annotations

import json
import math
from pathlib import Path


def run_simulation() -> dict:
    xs = [i * 0.2 for i in range(51)]
    ys = [math.sin(x) for x in xs]
    return {"x": xs, "y": ys}


def main() -> None:
    out_path = Path(__file__).resolve().parent / "sim_data.json"
    data = run_simulation()
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
