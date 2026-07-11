from functools import lru_cache

from lynx.store.memory_store import InMemorySessionStore


@lru_cache(maxsize=1)
def get_store() -> InMemorySessionStore:
    return InMemorySessionStore()
