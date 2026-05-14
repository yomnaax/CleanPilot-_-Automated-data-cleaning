"""
Metrics instrumentation placeholder.
"""


def record(event: str, payload: dict | None = None):
    return {"event": event, "payload": payload or {}}

