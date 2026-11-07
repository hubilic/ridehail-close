import argparse
import sys
from pathlib import Path

from ridehail import db

DATA_DIR = Path("/data")
REFERENCE_DIR = DATA_DIR / "reference"
INCOMING_DIR = DATA_DIR / "incoming"
REPORTS_DIR = Path("/reports")


def cmd_close(args: argparse.Namespace) -> int:
    print(db.describe())
    applied = db.apply_schema()
    print(f"schema {len(applied)} file{'s' if len(applied) != 1 else ''} applied")

    # TODO: load REFERENCE_DIR / "cities.csv" and "drivers.csv"
    # TODO: load every INCOMING_DIR / "trips_*.csv", in file-name order,
    #          printing one reconciliation line per file
    # TODO: write the reports into REPORTS_DIR
    print("TODO reference data, trip files, reports")
    return 0


def cmd_load(args: argparse.Namespace) -> int:
    # TODO: load a single trip file (args.path) under the same rules as close
    print(f"load: not implemented yet ({args.path})", file=sys.stderr)
    return 1


def cmd_report(args: argparse.Namespace) -> int:
    # TODO: write the report CSVs into REPORTS_DIR
    print("report: not implemented yet", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ridehail", description="Ridehail Daily Close")
    sub = parser.add_subparsers(dest="command", metavar="command")

    p = sub.add_parser("close", help="run the full daily close (default)")
    p.set_defaults(func=cmd_close)

    p = sub.add_parser("load", help="load one trip file")
    p.add_argument("path", type=Path, help="e.g. /data/incoming/trips_2026-10-19.csv")
    p.set_defaults(func=cmd_load)

    p = sub.add_parser("report", help="write the report CSVs")
    p.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        args = parser.parse_args(["close"])
    try:
        return args.func(args)
    except db.DatabaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()
