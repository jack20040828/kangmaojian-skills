#!/usr/bin/env python3
"""Run deterministic review comparisons using only explicitly supplied inputs."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def number(value: str, name: str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def rendered(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP).normalize(), "f")


def compare_minimum(args: argparse.Namespace) -> dict:
    actual = number(args.actual, "actual")
    minimum = number(args.minimum, "minimum")
    return {
        "calculation": "minimum_comparison",
        "inputs": {"name": args.name, "actual": rendered(actual), "minimum": rendered(minimum), "unit": args.unit},
        "method": "actual >= minimum",
        "result": "compliant" if actual >= minimum else "noncompliant",
        "margin": rendered(actual - minimum),
    }


def egress_width(args: argparse.Namespace) -> dict:
    occupants = number(args.occupants, "occupants")
    width_per_100 = number(args.width_per_100, "width_per_100")
    provided = number(args.provided, "provided")
    if occupants < 0 or width_per_100 <= 0 or provided < 0:
        raise ValueError("occupants and provided must be non-negative; width_per_100 must be positive")
    required = occupants * width_per_100 / Decimal(100)
    return {
        "calculation": "egress_width",
        "inputs": {
            "occupants": rendered(occupants),
            "width_per_100_people_m": rendered(width_per_100),
            "provided_width_m": rendered(provided),
        },
        "method": "required_width = occupants * width_per_100_people / 100",
        "required_width_m": rendered(required),
        "result": "compliant" if provided >= required else "noncompliant",
        "margin_m": rendered(provided - required),
    }


def slope(args: argparse.Namespace) -> dict:
    rise = number(args.rise_mm, "rise_mm")
    run = number(args.run_mm, "run_mm")
    max_ratio = number(args.max_ratio, "max_ratio")
    if rise <= 0 or run <= 0 or max_ratio <= 0:
        raise ValueError("rise_mm, run_mm, and max_ratio must be positive")
    actual_ratio = run / rise
    return {
        "calculation": "slope_ratio",
        "inputs": {"rise_mm": rendered(rise), "run_mm": rendered(run), "maximum_slope": f"1:{rendered(max_ratio)}"},
        "method": "actual_ratio = run / rise; compliant when actual_ratio >= required ratio denominator",
        "actual_slope": f"1:{rendered(actual_ratio)}",
        "result": "compliant" if actual_ratio >= max_ratio else "noncompliant",
    }


def count_range(args: argparse.Namespace) -> dict:
    actual = number(args.actual, "actual")
    minimum = number(args.minimum, "minimum")
    maximum = number(args.maximum, "maximum")
    if minimum > maximum:
        raise ValueError("minimum cannot exceed maximum")
    return {
        "calculation": "range_comparison",
        "inputs": {"name": args.name, "actual": rendered(actual), "minimum": rendered(minimum), "maximum": rendered(maximum)},
        "method": "minimum <= actual <= maximum",
        "result": "compliant" if minimum <= actual <= maximum else "noncompliant",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    minimum = subparsers.add_parser("compare-minimum", help="compare an observed dimension with a minimum")
    minimum.add_argument("--name", required=True)
    minimum.add_argument("--actual", required=True)
    minimum.add_argument("--minimum", required=True)
    minimum.add_argument("--unit", required=True)
    minimum.set_defaults(handler=compare_minimum)

    egress = subparsers.add_parser("egress-width", help="calculate required total egress width")
    egress.add_argument("--occupants", required=True)
    egress.add_argument("--width-per-100", required=True, help="metres per 100 people from the applicable rule")
    egress.add_argument("--provided", required=True, help="provided total effective width in metres")
    egress.set_defaults(handler=egress_width)

    ramp = subparsers.add_parser("slope", help="compare a measured slope with a 1:n maximum")
    ramp.add_argument("--rise-mm", required=True)
    ramp.add_argument("--run-mm", required=True)
    ramp.add_argument("--max-ratio", required=True, help="n in maximum slope 1:n")
    ramp.set_defaults(handler=slope)

    count = subparsers.add_parser("count-range", help="compare a count with an inclusive range")
    count.add_argument("--name", required=True)
    count.add_argument("--actual", required=True)
    count.add_argument("--minimum", required=True)
    count.add_argument("--maximum", required=True)
    count.set_defaults(handler=count_range)

    args = parser.parse_args()
    try:
        result = args.handler(args)
    except ValueError as error:
        print(f"FAIL: {error}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
