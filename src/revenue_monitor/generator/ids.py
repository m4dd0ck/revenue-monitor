"""Deterministic Stripe-style object IDs."""

import random
import string

_ALPHABET = string.digits + string.ascii_letters


class IdFactory:
    """Mints IDs like ``cus_4fQ2...`` from a seeded RNG so reruns produce identical IDs."""

    def __init__(self, rng: random.Random, length: int = 14) -> None:
        self._rng = rng
        self._length = length
        self._issued: set[str] = set()

    def new(self, prefix: str) -> str:
        """Return an unused ID with the given Stripe prefix (``cus``, ``sub``, ...)."""
        while True:
            suffix = "".join(self._rng.choice(_ALPHABET) for _ in range(self._length))
            candidate = f"{prefix}_{suffix}"
            if candidate not in self._issued:
                self._issued.add(candidate)
                return candidate
