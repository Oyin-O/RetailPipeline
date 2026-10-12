"""Command line entry point: `retail-pipeline <stage>`."""

import argparse
import sys
from pathlib import Path

from retail_pipeline import oltp, pipeline, simulator
from retail_pipeline.config import Settings, load_settings
from retail_pipeline.extract import TABLES


def _init_db(settings: Settings, args: argparse.Namespace) -> int:
    with oltp.connect(settings.oltp_dsn) as conn:
        oltp.apply_schema(conn, args.schema)
    print(f"applied {args.schema}")
    return 0


def _simulate(settings: Settings, args: argparse.Namespace) -> int:
    with oltp.connect(settings.oltp_dsn) as conn:
        days = simulator.simulate(
            conn,
            days=args.days,
            seed=args.seed,
            new_users=args.new_users,
            updates=args.updates,
            dirty_rate=args.dirty_rate,
        )
    for day in days:
        print(f"{day.day}: {day.users_created} users created, {day.users_updated} updated")
    return 0


def _extract(settings: Settings, args: argparse.Namespace) -> int:
    for result in pipeline.extract_all(settings, args.tables):
        window = f"({result.low.isoformat() if result.low else 'start'}, {result.high.isoformat()}]"
        print(f"extract {result.table}: {result.row_count} rows in {window}")
    return 0


def _ingest(settings: Settings, args: argparse.Namespace) -> int:
    result = pipeline.build_silver_users(settings)
    print(f"ingest {result.dataset}: {result.valid} valid, {result.rejected} rejected")
    return 0


def _transform(settings: Settings, args: argparse.Namespace) -> int:
    for model in pipeline.build_warehouse(settings):
        print(f"built {model}")
    return 0


def _check(settings: Settings, args: argparse.Namespace) -> int:
    results = pipeline.run_checks(settings)
    for result in results:
        status = "ok" if result.passed else f"FAILED ({result.failing_rows} rows)"
        print(f"check {result.name}: {status}")
    return 0 if all(result.passed for result in results) else 1


def _run(settings: Settings, args: argparse.Namespace) -> int:
    args.tables = None
    for stage in (_extract, _ingest, _transform, _check):
        code = stage(settings, args)
        if code != 0:
            return code
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="retail-pipeline", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init_db = commands.add_parser("init-db", help="create the OLTP tables")
    init_db.add_argument("--schema", type=Path, default=oltp.DEFAULT_SCHEMA_PATH)
    init_db.set_defaults(handler=_init_db)

    simulate = commands.add_parser("simulate", help="generate application activity in the OLTP")
    simulate.add_argument("--days", type=int, default=1)
    simulate.add_argument("--seed", type=int, default=42)
    simulate.add_argument("--new-users", type=int, default=20, help="signups per day")
    simulate.add_argument("--updates", type=int, default=3, help="user changes per day")
    simulate.add_argument("--dirty-rate", type=float, default=0.05)
    simulate.set_defaults(handler=_simulate)

    extract = commands.add_parser("extract", help="pull new and changed OLTP rows into bronze")
    extract.add_argument("--tables", nargs="+", choices=sorted(TABLES))
    extract.set_defaults(handler=_extract)

    ingest = commands.add_parser("ingest", help="validate bronze into silver, quarantine rejects")
    ingest.set_defaults(handler=_ingest)

    transform = commands.add_parser("transform", help="build the warehouse models")
    transform.set_defaults(handler=_transform)

    check = commands.add_parser("check", help="run data quality checks on the warehouse")
    check.set_defaults(handler=_check)

    run = commands.add_parser("run", help="extract, ingest, transform and check")
    run.set_defaults(handler=_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(load_settings(), args)


if __name__ == "__main__":
    sys.exit(main())
