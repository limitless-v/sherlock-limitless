#!/usr/bin/env python3
"""Create local data directories and verify .env exists."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = ["uploads", "cache", "embeddings", "results", "logs", "models", "data"]


def main() -> None:
    for name in DIRS:
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    env_example = ROOT / ".env.example"
    env_file = ROOT / ".env"
    if not env_file.exists() and env_example.exists():
        print("Copy .env.example to .env and adjust values.")
    print("Storage directories ready.")


if __name__ == "__main__":
    main()
