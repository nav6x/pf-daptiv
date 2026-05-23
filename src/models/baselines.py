from typing import Dict, Any
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.ensemble import RandomForestClassifier


class BaselineMLP(nn.Module):
    def __init__(
        self,
        input_dim: int = 35,
        hidden_dim1: int = 128,
        hidden_dim2: int = 64,
        num_classes: int = 7,
    ):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim1)
        self.bn1 = nn.BatchNorm1d(hidden_dim1)
        self.fc2 = nn.Linear(hidden_dim1, hidden_dim2)
        self.bn2 = nn.BatchNorm1d(hidden_dim2)
        self.dropout = nn.Dropout(p=0.3)
        self.fc_out = nn.Linear(hidden_dim2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 3:
            x = x.squeeze(1)
        h1 = F.relu(self.bn1(self.fc1(x)))
        h2 = F.relu(self.bn2(self.fc2(h1)))
        h2 = self.dropout(h2)
        return self.fc_out(h2)


def get_random_forest_baseline(
    n_estimators: int = 100, random_state: int = 42
) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=15,
        min_samples_split=4,
        n_jobs=1,
        random_state=random_state,
    )
