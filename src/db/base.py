"""Import all model modules so SQLModel.metadata discovers every table.

Used by Alembic env.py for autogenerate and by init_db() as a fallback.
"""

from sqlmodel import SQLModel

from ..auth import models as _auth_models  # noqa: F401
from . import models_citations as _citations  # noqa: F401
from . import models_documents as _documents  # noqa: F401
from . import models_ingestion as _ingestion  # noqa: F401

metadata = SQLModel.metadata

__all__ = ["metadata"]
