
import os
import sys
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.synthetic_apt import generate_synthetic_corpus, partition_data_across_clients
from src.data.dataset_loader import CDFVDataset
from src.models.cnn1d import APTClassifier1DCNN
from src.models.baselines import BaselineMLP, get_random_forest_baseline
from src.federated.privacy import DifferentialPrivacyManager
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer
from src.utils.metrics import evaluate_predictions




def train_centralized(model, train_loader, test_loader, epochs=5, lr=0.001, device="cpu"):
    model = model.to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    model.train()
    for _ in range(epochs):
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            optimizer.step()

    model.eval()
    all_preds, all_probs, all_targets = [], [], []
    with torch.no_grad():
        for bx, by in test_loader:
            bx = bx.to(device)
            probs = torch.softmax(model(bx), dim=-1)
            preds = torch.argmax(probs, dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
            all_targets.extend(by.numpy())

    return evaluate_predictions(all_targets, all_preds, all_probs)


def main():
    parser = argparse.ArgumentParser(description="Baseline model benchmarking")
    parser.add_argument("--samples", type=int, default=2500, help="Evaluation samples")
    parser.add_argument("--rounds", type=int, default=5, help="Federated rounds")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    df, y_multi, _ = generate_synthetic_corpus(total_samples=args.samples, random_state=42)
    x = df.values
    split = int(len(x) * 0.8)
    x_train, x_test = x[:split], x[split:]
    y_train, y_test = y_multi[:split], y_multi[split:]

    train_ds = CDFVDataset(x_train, y_train)
    test_ds = CDFVDataset(x_test, y_test)
    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=128, shuffle=False)

    results = {}

    print("[*] 1/5: fitting random forest baseline...")
    rf = get_random_forest_baseline()
    rf.fit(x_train, y_train)
    results["Random Forest"] = (
        evaluate_predictions(y_test, rf.predict(x_test), rf.predict_proba(x_test)),
        "Centralized",
    )

    print("[*] 2/5: training mlp baseline...")
    mlp = BaselineMLP(input_dim=35, num_classes=7)
    results["Centralized MLP"] = (
        train_centralized(mlp, train_loader, test_loader, epochs=6, device=args.device),
        "Centralized",
    )

    print("[*] 3/5: training centralized 1d-cnn upper bound...")
    cnn = APTClassifier1DCNN(input_dim=35, num_classes=7)
    results["Centralized 1D-CNN"] = (
        train_centralized(cnn, train_loader, test_loader, epochs=6, device=args.device),
        "Centralized",
    )

    print("[*] 4/5: running non-private fedavg...")
    partitions = partition_data_across_clients(x_train, y_train, num_clients=3)
    dp_none = DifferentialPrivacyManager(epsilon=0.0, clip_threshold=1.0, dual_layer=False)

    def model_fn():
        return APTClassifier1DCNN(input_dim=35, num_classes=7)

    clients_np = [
        FederatedClient(i, CDFVDataset(px, py), model_fn, dp_none, local_epochs=2, device=args.device)
        for i, (px, py) in enumerate(partitions)
    ]
    server_np = FederatedServer(model_fn(), clients_np, dp_none, test_ds, device=args.device)
    for r in range(1, args.rounds + 1):
        server_np.run_round(r)
    results["FedAvg (No DP)"] = (server_np.evaluate(), "Federated (No DP)")

    print("[*] 5/5: running pf-daptiv with dual-layer dp...")
    dp_priv = DifferentialPrivacyManager(epsilon=1.0, delta=1e-5, clip_threshold=1.0, dual_layer=True)
    clients_priv = [
        FederatedClient(i, CDFVDataset(px, py), model_fn, dp_priv, local_epochs=2, device=args.device)
        for i, (px, py) in enumerate(partitions)
    ]
    server_priv = FederatedServer(model_fn(), clients_priv, dp_priv, test_ds, device=args.device)
    for r in range(1, args.rounds + 1):
        server_priv.run_round(r)
    results["PF-DAPTIV"] = (server_priv.evaluate(), "eps=1.0, d=1e-5")

    print("\nBenchmark Summary:")
    print(f"{'Model / Framework':<24}{'Mode':<22}{'Binary Acc':<14}{'Macro-F1':<12}{'MCC':<10}")
    print("-" * 82)
    for name, (metrics, mode_desc) in results.items():
        acc = f"{metrics['binary_accuracy'] * 100:.2f}%"
        f1 = f"{metrics['f1_macro'] * 100:.2f}%"
        mcc = f"{metrics['binary_mcc']:.4f}"
        print(f"{name:<24}{mode_desc:<22}{acc:<14}{f1:<12}{mcc:<10}")
    print("-" * 82 + "\n")


if __name__ == "__main__":
    main()
