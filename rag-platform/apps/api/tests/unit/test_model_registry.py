import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[2]


def test_app_imports_resolve_every_foreign_key():
    """
    In a fresh interpreter, importing only what the app imports must give
    SQLAlchemy every table that a foreign key points at. Run in a
    subprocess so models imported by other tests can't hide a gap.
    """
    script = (
        "import src.routers.chat, src.routers.upload\n"
        "from src.models.base import Base\n"
        "from sqlalchemy.orm import configure_mappers\n"
        "configure_mappers()\n"
        "Base.metadata.sorted_tables\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=API_DIR, capture_output=True, text=True,
        env={"ANONYMIZED_TELEMETRY": "False", "PATH": "/usr/bin:/bin"},
    )

    assert result.returncode == 0, result.stderr[-2000:]
