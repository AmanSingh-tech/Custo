from __future__ import annotations

import math


class TemperatureCalibrator:
    def __init__(self, temperature: float = 1.25) -> None:
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        self.temperature = temperature

    def calibrate(self, probability: float) -> float:
        bounded = min(1.0 - 1e-7, max(1e-7, probability))
        logit = math.log(bounded / (1.0 - bounded))
        return 1.0 / (1.0 + math.exp(-logit / self.temperature))

