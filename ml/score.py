#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.scoring_service import FilterOptions, ScoringService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Subsidy scoring CLI")
    parser.add_argument("--input", default="Data.xlsx", help="Path to xlsx/csv/json file")
    parser.add_argument("--target", default="", help="Optional target column")
    parser.add_argument("--id-column", default="", help="Optional id column")
    parser.add_argument("--shortlist", default="20", help="Shortlist size")
    parser.add_argument("--region", default="", help="Optional region filter")
    parser.add_argument("--farm-size", default="", help="Optional farm size filter: small/medium/large")
    parser.add_argument("--subsidy-type", default="", help="Optional subsidy type filter")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = ScoringService()
    result = service.run_scoring(
        input_path=args.input,
        shortlist_n=max(1, int(args.shortlist)),
        target_column=args.target.strip() or None,
        id_column=args.id_column.strip() or None,
        filters=FilterOptions(
            region=args.region.strip() or None,
            farm_size=args.farm_size.strip() or None,
            subsidy_type=args.subsidy_type.strip() or None,
        ),
    )
    print(result.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
