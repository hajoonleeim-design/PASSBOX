import argparse
import json
from pathlib import Path

from app.db import Settings, get_session_factory
from app.retention import cleanup_storage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview or apply PASSBOX document storage retention cleanup."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete expired terminal document files. Without this flag, only preview.",
    )
    args = parser.parse_args()
    settings = Settings()
    summary = cleanup_storage(
        get_session_factory(),
        storage_root=Path(settings.storage_root),
        apply=args.apply,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
