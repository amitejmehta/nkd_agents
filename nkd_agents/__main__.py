#!/usr/bin/env python3
"""
Entry point for nkd_agents CLI
"""

import asyncio
from .cli.sandbox import run_sandbox


def main() -> None:
    asyncio.run(run_sandbox())


if __name__ == "__main__":
    main()
