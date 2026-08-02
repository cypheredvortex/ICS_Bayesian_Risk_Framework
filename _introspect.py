"""Temporary introspection script for SQLAlchemy models."""

import backend.database.models as m

names = [
    n
    for n in dir(m)
    if isinstance(getattr(m, n), type) and getattr(m, n).__module__ == "backend.database.models"
]
print(len(names))
for n in sorted(names):
    cls = getattr(m, n)
    try:
        cols = [c.name for c in cls.__table__.columns]
        print(f"{n}: {cols}")
    except Exception as e:  # noqa: BLE001
        print(f"{n}: ERROR {e}")

