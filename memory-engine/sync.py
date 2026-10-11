"""Pure transformation: generated Memory + DB snapshot -> idempotent sync suggestions.

This service is deliberately stateless. Spring Boot must upsert on memory_id
and persist content_hash for retry safety. Nothing is saved here.
"""
import hashlib
import json
from typing import Any


def memory_content_hash(memory: dict[str, Any]) -> str:
    """Hash meaningful output only; dict order cannot affect the result."""
    canonical = json.dumps(memory, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def annotate_changes(generated: list[dict], existing: dict[str, str | None]) -> list[dict]:
    result = []
    for original in generated:
        digest = memory_content_hash(original)
        memory_id = original["memory_id"]
        if memory_id not in existing:
            action = "CREATE"
        elif existing[memory_id] == digest:
            action = "UNCHANGED"
        else:
            action = "UPDATE"
        result.append({**original, "content_hash": digest, "sync_action": action})
    return result


def missing_memory_ids(generated: list[dict], scoped_existing_ids: list[str]) -> list[str]:
    """Core supplies only the authoritative user's explicitly complete month scopes."""
    active = {memory["memory_id"] for memory in generated}
    return sorted(set(scoped_existing_ids) - active)
