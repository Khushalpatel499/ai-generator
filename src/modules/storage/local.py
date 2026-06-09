"""Local file storage module."""
import shutil
import json
from pathlib import Path
from typing import Optional
from src.core.interfaces import BaseStorage
from src.core.config import Config


class LocalStorage(BaseStorage):
    """Stores outputs on local filesystem with job tracking."""

    def __init__(self, config: Config):
        self.config = config
        self.jobs_file = config.output_dir / "jobs.json"
        self._ensure_jobs_file()

    def _ensure_jobs_file(self):
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        if not self.jobs_file.exists():
            self.jobs_file.write_text("{}")

    def save(self, file_path: str, job_id: str) -> str:
        src = Path(file_path)
        dest = self.config.output_dir / f"{job_id}_final.mp4"

        if src != dest:
            shutil.move(str(src), str(dest))

        # Track in jobs file
        jobs = json.loads(self.jobs_file.read_text())
        jobs[job_id] = str(dest)
        self.jobs_file.write_text(json.dumps(jobs, indent=2))

        return str(dest)

    def get_path(self, job_id: str) -> Optional[str]:
        jobs = json.loads(self.jobs_file.read_text())
        return jobs.get(job_id)
