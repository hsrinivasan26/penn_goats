"""Seeded randomness so a given seed reproduces the exact same game (reproducible = verifiable)."""

import random


class SeededRNG:
    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)
        self.seed = seed

    def draw_normal(self, mu: float, sigma: float) -> float:
        """One sample from Normal(mu, sigma); sigma 0 returns mu exactly."""
        return mu if sigma == 0 else self._rng.normalvariate(mu, sigma)

    def draw_int(self, low: int, high: int) -> int:
        """Uniform integer in [low, high], inclusive."""
        return self._rng.randint(low, high)

    def roll_bucket(self, buckets: list) -> dict:
        """Pick one event bucket by its 'prob' weight (list order matters)."""
        roll = self._rng.uniform(0, 100)
        cumulative = 0.0
        for bucket in buckets:
            cumulative += bucket["prob"]
            if roll < cumulative:
                return bucket
        return buckets[-1]
