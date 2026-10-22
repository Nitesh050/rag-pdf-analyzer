"""
Imports every model so SQLAlchemy knows all tables before the first query.

Foreign keys refer to tables by name (message_sources.chunk_id -> chunks),
so a model the app never imports directly (e.g. Chunk) would leave that
reference unresolved and saving would fail. src/db/session.py imports this
module; add new models here.
"""

from .chunk import Chunk  # noqa: F401
from .conversation import Conversation, Message, MessageSource  # noqa: F401
from .document import Document  # noqa: F401
from .user import User, UserSession  # noqa: F401
