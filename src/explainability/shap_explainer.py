from typing import List, Dict, Tuple
import numpy as np
import torch

from ..data.cdfv_schema import CDFV_FEATURE_NAMES


class ModelWrapper:

    def __init__(self, model: torch.nn.Module, device: str = "cpu"):
        self.model = model.to(device)
        self.model.eval()
        self.device = device

    def __call__(self, x: np.ndarray) -> np.ndarray:
        tensor_x = torch.tensor(x, dtype=torch.float32).to(self.device)
        with torch.no_grad():
            logits = self.model(tensor_x)
            probs = torch.softmax(logits, dim=-1)
        return probs.cpu().numpy()


class SHAPExplainer:
    def __init__(
        self, model: torch.nn.Module, background_data: np.ndarray, device: str = "cpu"
    ):
        self.model = model
        self.background_data = background_data
        self.device = device
        self.wrapper = ModelWrapper(model, device=device)

    def compute_feature_importance(
        self, test_samples: np.ndarray, num_samples: int = 50
    ) -> Dict[str, float]:
        eval_samples = test_samples[:num_samples]
        baseline_preds = self.wrapper(eval_samples)

        feature_importance = {}
        for i, feat_name in enumerate(CDFV_FEATURE_NAMES):
            perturbed = eval_samples.copy()
            perturbed[:, i] = np.mean(self.background_data[:, i])

            perturbed_preds = self.wrapper(perturbed)
            impact = np.mean(np.abs(baseline_preds - perturbed_preds))
            feature_importance[feat_name] = float(impact)

        total = sum(feature_importance.values()) or 1.0
        normalized = {k: v / total for k, v in feature_importance.items()}

        return dict(sorted(normalized.items(), key=lambda item: item[1], reverse=True))

    def extract_chifs(
        self, feature_importance: Dict[str, float], top_k: int = 8
    ) -> List[Tuple[str, float]]:
        return list(feature_importance.items())[:top_k]
