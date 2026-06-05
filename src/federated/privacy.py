import math
from typing import Dict
import torch


class DifferentialPrivacyManager:

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        clip_threshold: float = 1.0,
        dual_layer: bool = True,
    ):
        self.epsilon = epsilon
        self.delta = delta
        self.clip_threshold = clip_threshold
        self.dual_layer = dual_layer

        self.sigma = 0.0
        if epsilon > 0:
            self.sigma = (clip_threshold / epsilon) * math.sqrt(2.0 * math.log(1.25 / delta))

    def clip_model_delta(
        self, model_delta: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        total_norm_sq = sum(
            p.pow(2).sum().item()
            for p in model_delta.values()
            if p.dtype in (torch.float32, torch.float64)
        )
        total_norm = math.sqrt(total_norm_sq)
        scale = min(1.0, self.clip_threshold / (total_norm + 1e-8))

        return {
            k: (v * scale if v.dtype in (torch.float32, torch.float64) else v.clone())
            for k, v in model_delta.items()
        }

    def add_gaussian_noise(
        self,
        tensors: Dict[str, torch.Tensor],
        num_samples: int = 500,
        scale_factor: float = 1.0,
    ) -> Dict[str, torch.Tensor]:
        if self.epsilon <= 0 or self.sigma <= 0:
            return tensors

        effective_sigma = (self.sigma / max(1, num_samples)) * scale_factor

        noised = {}
        for k, v in tensors.items():
            if v.dtype in (torch.float32, torch.float64):
                noised[k] = v + torch.randn_like(v) * effective_sigma
            else:
                noised[k] = v.clone()

        return noised
