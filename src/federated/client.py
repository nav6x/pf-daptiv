import copy
from typing import Dict, Any, Tuple
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from ..data.dataset_loader import CDFVDataset, compute_class_weights
from .privacy import DifferentialPrivacyManager


class FederatedClient:
    def __init__(
        self,
        client_id: int,
        dataset: CDFVDataset,
        model_fn: Any,
        dp_manager: DifferentialPrivacyManager,
        batch_size: int = 64,
        local_epochs: int = 5,
        lr: float = 0.001,
        weight_decay: float = 1e-4,
        device: str = "cpu",
    ):
        self.client_id = client_id
        self.dataset = dataset
        self.model_fn = model_fn
        self.dp_manager = dp_manager
        self.batch_size = batch_size
        self.local_epochs = local_epochs
        self.lr = lr
        self.weight_decay = weight_decay
        self.device = device

        self.dataloader = DataLoader(self.dataset, batch_size=self.batch_size, shuffle=True)

        labels_np = self.dataset.labels.numpy()
        self.class_weights = compute_class_weights(labels_np, num_classes=7).to(self.device)
        self.criterion = nn.CrossEntropyLoss(weight=self.class_weights)

    def train_epoch(
        self, global_state_dict: Dict[str, torch.Tensor]
    ) -> Tuple[Dict[str, torch.Tensor], float, int]:
        local_model = self.model_fn().to(self.device)
        local_model.load_state_dict(copy.deepcopy(global_state_dict))
        local_model.train()

        optimizer = optim.Adam(
            local_model.parameters(), lr=self.lr, weight_decay=self.weight_decay
        )

        total_loss = 0.0
        total_batches = 0

        for _ in range(self.local_epochs):
            for batch_x, batch_y in self.dataloader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)

                optimizer.zero_grad()
                logits = local_model(batch_x)
                loss = self.criterion(logits, batch_y)
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                total_batches += 1

        avg_loss = total_loss / max(1, total_batches)

        local_state = local_model.state_dict()
        model_delta = {
            k: local_state[k] - global_state_dict[k].to(self.device)
            for k in global_state_dict
        }

        clipped_delta = self.dp_manager.clip_model_delta(model_delta)

        if self.dp_manager.dual_layer:
            clipped_delta = self.dp_manager.add_gaussian_noise(
                clipped_delta,
                num_samples=len(self.dataset),
                scale_factor=0.5,
            )

        return clipped_delta, avg_loss, len(self.dataset)
