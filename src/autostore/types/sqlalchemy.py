"""SQLAlchemy types."""

import numpy as np
from sqlalchemy.types import JSON, TypeDecorator


class FloatArrayTypeDecorator(TypeDecorator):
    """Store NumPy arrays as JSON, load them back as NumPy arrays."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ANN201, ARG002, D102
        if value is None:
            return None
        if isinstance(value, np.ndarray):
            return value.tolist()
        return value

    def process_result_value(self, value, dialect):  # noqa: ANN001, ANN201, ARG002, D102
        if value is None:
            return None
        return np.array(value, dtype=float)
