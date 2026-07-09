# RNG classes!!
# Ask Gemini or Claude to explain how to use these

import random


class SeededRNG:
    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)
        self.seed = seed

    # Gaussian distribution RNG (true-r RNG)
    def draw_normal(self, mu: float, sigma: float) -> float:
        return mu if sigma == 0 else self._rng.normalvariate(mu, sigma)

    # Inclusive RNG
    def draw_int(self, low: int, high: int) -> int:
        return self._rng.randint(low, high)

    # Pick one event bucket by its ["prob"] weight (ordered list)
    def roll_bucket(self, buckets: list) -> dict:
        roll = self._rng.uniform(0, 100)
        cumulative = 0.0
        for bucket in buckets:
            cumulative += bucket["prob"]
            if roll < cumulative:
                return bucket
        return buckets[-1]
