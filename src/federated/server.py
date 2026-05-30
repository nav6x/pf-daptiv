import copy
from typing import List, Dict, Tuple, Any
import torch
from torch.utils.data import DataLoader

from .client import FederatedClient
from .privacy import DifferentialPrivacyManager
from ..utils.metrics import evaluate_predictions


class FederatedServer:
    def __init__(
        self,
        global_model: torch.nn.Module,
        clients: List[FederatedClient],
        dp_manager: DifferentialPrivacyManager,
        test_dataset: Any,
        device: str = "cpu",
    ):
        self.global_model = global_model.to(device)
        self.clients = clients
        self.dp_manager = dp_manager
        self.test_dataset = test_dataset
        self.device = device

        self.test_loader = DataLoader(self.test_dataset, batch_size=128, shuffle=False)

    def aggregate_updates(
        self, client_updates: List[Tuple[Dict[str, torch.Tensor], int]]
    ) -> Dict[str, torch.Tensor]:
        total_samples = sum(n for _, n in client_updates)
        first_delta = client_updates[0][0]

        aggregated = {
            k: (torch.zeros_like(v) if v.dtype in (torch.float32, torch.float64) else v.clone())
            for k, v in first_delta.items()
        }

        for delta, n in client_updates:
            weight = n / max(1, total_samples)
            for k, acc in aggregated.items():
                if delta[k].dtype in (torch.float32, torch.float64):
                    acc.add_(delta[k] * weight)

        if self.dp_manager.dual_layer:
            aggregated = self.dp_manager.add_gaussian_noise(
                aggregated, num_samples=total_samples, scale_factor=0.5
            )

        return aggregated

    def apply_update(self, aggregated_delta: Dict[str, torch.Tensor]):
        global_state = self.global_model.state_dict()
        for k, param in global_state.items():
            if aggregated_delta[k].dtype in (torch.float32, torch.float64):
                param.add_(aggregated_delta[k].to(self.device))
            else:
                global_state[k] = aggregated_delta[k].to(self.device)
        self.global_model.load_state_dict(global_state)

    def evaluate(self) -> Dict[str, float]:
        self.global_model.eval()
        all_preds = []
        all_probs = []
        all_targets = []

        with torch.no_grad():
            for batch_x, batch_y in self.test_loader:
                batch_x = batch_x.to(self.device)
                logits = self.global_model(batch_x)
                probs = torch.softmax(logits, dim=-1)
                preds = torch.argmax(probs, dim=-1)

                all_preds.extend(preds.cpu().numpy())
                all_probs.extend(probs.cpu().numpy())
                all_targets.extend(batch_y.numpy())

        return evaluate_predictions(all_targets, all_preds, all_probs)

    def run_round(self, round_num: int) -> Tuple[float, Dict[str, float]]:
        client_updates = []
        client_losses = []
        global_state = copy.deepcopy(self.global_model.state_dict())

        for client in self.clients:
            delta, loss, num_samples = client.train_epoch(global_state)
            client_updates.append((delta, num_samples))
            client_losses.append(loss)

        avg_loss = sum(client_losses) / len(client_losses)
        aggregated = self.aggregate_updates(client_updates)
        self.apply_update(aggregated)

        return avg_loss, self.evaluate()
