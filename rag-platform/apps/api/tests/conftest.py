import os
import sys
import tempfile
import warnings
from pathlib import Path

# Tests must never write into the app's real index (data/chroma_db).
# Point every VectorStore at a throwaway directory before anything imports it.
os.environ["CHROMA_DIR"] = tempfile.mkdtemp(prefix="rag-test-chroma-")

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
