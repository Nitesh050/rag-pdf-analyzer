import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

warnings.filterwarnings(
    "ignore",
    message=r".*asyncio\.iscoroutinefunction.*",
    category=DeprecationWarning,
    module=r"chromadb\.telemetry\.opentelemetry",
)

warnings.filterwarnings(
    "ignore",
    message=r".*deprecated and slated for removal.*",
    category=DeprecationWarning,
)
