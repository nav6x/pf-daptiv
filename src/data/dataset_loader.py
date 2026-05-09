from typing import Tuple
import numpy as np
import torch
from torch.utils.data import Dataset


class CDFVDataset(Dataset):
    def __init__(self, features: np.ndarray, labels: np.ndarray):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]


def apply_local_smote(
    x: np.ndarray,
    y: np.ndarray,
    target_apt_ratio: float = 0.33,
    k_neighbors: int = 5,
) -> Tuple[np.ndarray, np.ndarray]:
    unique_classes, counts = np.unique(y, return_counts=True)
    benign_count = counts[0] if unique_classes[0] == 0 else counts[unique_classes == 0][0]

    num_minority_classes = max(1, len(unique_classes) - 1)
    target_per_class = int((benign_count * target_apt_ratio) / num_minority_classes)

    synthetic_x = []
    synthetic_y = []

    for c in unique_classes:
        if c == 0:
            continue
        c_samples = x[y == c]
        current_count = len(c_samples)

        if 1 < current_count < target_per_class:
            diff = target_per_class - current_count
            k = min(k_neighbors, current_count - 1)

            for _ in range(diff):
                idx1 = np.random.randint(0, current_count)
                dists = np.linalg.norm(c_samples - c_samples[idx1], axis=1)
                neighbor_pool = np.argsort(dists)[1 : k + 1]
                idx2 = np.random.choice(neighbor_pool) if len(neighbor_pool) > 0 else idx1

                lam = np.random.uniform(0.0, 1.0)
                synth = c_samples[idx1] + lam * (c_samples[idx2] - c_samples[idx1])
                synthetic_x.append(synth)
                synthetic_y.append(c)

    if synthetic_x:
        new_x = np.vstack([x, np.array(synthetic_x, dtype=np.float32)])
        new_y = np.concatenate([y, np.array(synthetic_y, dtype=np.int64)])
        p = np.random.permutation(len(new_y))
        return new_x[p], new_y[p]

    return x, y


def compute_class_weights(labels: np.ndarray, num_classes: int = 7) -> torch.Tensor:
    total = len(labels)
    weights = np.zeros(num_classes, dtype=np.float32)
    for c in range(num_classes):
        count = np.sum(labels == c)
        weights[c] = total / (num_classes * count) if count > 0 else 1.0

    weights /= np.mean(weights)
    return torch.tensor(weights, dtype=torch.float32)
