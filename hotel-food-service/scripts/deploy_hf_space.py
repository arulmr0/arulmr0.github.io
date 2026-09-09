"""Publish this directory to a Hugging Face Space (Docker SDK).

Used by .github/workflows/hotel-food-service-deploy.yml. Needs:
  HF_TOKEN   write token (https://huggingface.co/settings/tokens)
  HF_SPACE   optional "owner/name"; defaults to "<token owner>/hotel-food-service"

Run locally:  pip install huggingface_hub && python scripts/deploy_hf_space.py
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
SPACE_FRONT_MATTER = """---
title: Hotel Food Service
emoji: 🍽️
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 8000
pinned: false
---
"""
IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache", "*.egg-info", "*.db", ".env", ".venv"
)


def main() -> int:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN is not set; skipping deploy.")
        return 0
    api = HfApi(token=token)
    space = os.environ.get("HF_SPACE") or f"{api.whoami()['name']}/hotel-food-service"

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "space"
        shutil.copytree(ROOT, staging, ignore=IGNORE)
        readme = staging / "README.md"
        readme.write_text(SPACE_FRONT_MATTER + readme.read_text())

        api.create_repo(space, repo_type="space", space_sdk="docker", exist_ok=True)
        api.add_space_variable(space, "HFS_SEED_ON_START", "true")
        secret = os.environ.get("HFS_SECRET_KEY")
        if secret:
            api.add_space_secret(space, "HFS_SECRET_KEY", secret)
        api.upload_folder(
            folder_path=str(staging),
            repo_id=space,
            repo_type="space",
            commit_message="Deploy hotel-food-service",
        )
    print(f"Deployed to https://huggingface.co/spaces/{space}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
