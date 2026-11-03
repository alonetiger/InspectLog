"""CLI entrypoint for running InspectLog as a module (py -m inspectlog)."""

import sys

from inspectlog.app import run


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
