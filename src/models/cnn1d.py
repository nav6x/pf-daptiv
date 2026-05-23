from typing import Dict, Any
import torch
import torch.nn as nn
import torch.nn.functional as F


class APTClassifier1DCNN(nn.Module):
    def __init__(
        self,
        input_dim: int = 35,
        conv1_filters: int = 64,
        conv1_kernel: int = 3,
        conv2_filters: int = 128,
        conv2_kernel: int = 3,
        pool_size: int = 2,
        dense_units: int = 64,
        dropout_rate: float = 0.4,
        num_classes: int = 7,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes

        self.conv1 = nn.Conv1d(
            in_channels=1,
            out_channels=conv1_filters,
            kernel_size=conv1_kernel,
            padding=conv1_kernel // 2,
        )
        self.bn1 = nn.BatchNorm1d(conv1_filters)
        self.pool1 = nn.MaxPool1d(kernel_size=pool_size, stride=pool_size)

        self.conv2 = nn.Conv1d(
            in_channels=conv1_filters,
            out_channels=conv2_filters,
            kernel_size=conv2_kernel,
            padding=conv2_kernel // 2,
        )
        self.bn2 = nn.BatchNorm1d(conv2_filters)
        self.pool2 = nn.MaxPool1d(kernel_size=pool_size, stride=pool_size)

        with torch.no_grad():
            dummy = torch.zeros(1, 1, input_dim)
            x = self.pool1(F.relu(self.bn1(self.conv1(dummy))))
            x = self.pool2(F.relu(self.bn2(self.conv2(x))))
            flat_dim = x.view(1, -1).shape[1]

        self.fc1 = nn.Linear(flat_dim, dense_units)
        self.dropout = nn.Dropout(p=dropout_rate)
        self.fc_out = nn.Linear(dense_units, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 2:
            x = x.unsqueeze(1)

        h1 = self.pool1(F.relu(self.bn1(self.conv1(x))))
        h2 = self.pool2(F.relu(self.bn2(self.conv2(h1))))
        flat = h2.flatten(start_dim=1)
        z = self.dropout(F.relu(self.fc1(flat)))
        return self.fc_out(z)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        return F.softmax(self.forward(x), dim=-1)

    def predict_binary_proba(self, x: torch.Tensor) -> torch.Tensor:
        probs = self.predict_proba(x)
        apt_prob = torch.sum(probs[:, 1:], dim=-1, keepdim=True)
        benign_prob = probs[:, :1]
        return torch.cat([benign_prob, apt_prob], dim=-1)
