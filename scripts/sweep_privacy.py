
import os
import sys
import argparse
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.synthetic_apt import generate_synthetic_corpus, partition_data_across_clients
from src.data.dataset_loader import CDFVDataset
from src.models.cnn1d import APTClassifier1DCNN
from src.federated.privacy import DifferentialPrivacyManager
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer




def main():
    parser = argparse.ArgumentParser(description="Privacy budget epsilon sweep")
    parser.add_argument("--epsilons", nargs="+", type=float, default=[0.2, 0.5, 1.0, 2.0, 5.0], help="Epsilon values")
    parser.add_argument("--rounds", type=int, default=4, help="Rounds per evaluation")
    parser.add_argument("--samples", type=int, default=2000, help="Telemetry sample count")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    df, y_multi, _ = generate_synthetic_corpus(total_samples=args.samples, random_state=42)
    x = df.values
    split = int(len(x) * 0.8)
    x_train, x_test = x[:split], x[split:]
    y_train, y_test = y_multi[:split], y_multi[split:]

    test_ds = CDFVDataset(x_test, y_test)
    partitions = partition_data_across_clients(x_train, y_train, num_clients=3)

    def model_fn():
        return APTClassifier1DCNN(input_dim=35, num_classes=7)

    sweep_results = []

    for eps in args.epsilons:
        print("[*] evaluating epsilon = %.2f..." % eps)
        dp = DifferentialPrivacyManager(epsilon=eps, delta=1e-5, clip_threshold=1.0, dual_layer=True)
        clients = [
            FederatedClient(i, CDFVDataset(px, py), model_fn, dp, local_epochs=2, device=args.device)
            for i, (px, py) in enumerate(partitions)
        ]
        server = FederatedServer(model_fn(), clients, dp, test_ds, device=args.device)
        for r in range(1, args.rounds + 1):
            server.run_round(r)

        metrics = server.evaluate()
        sweep_results.append((eps, dp.sigma, metrics))

    print("\nPrivacy-Utility Trade-off Sweep:")
    print(f"{'Epsilon':<12}{'Sigma':<14}{'Accuracy':<14}{'Macro-F1':<12}{'MCC':<10}")
    print("-" * 62)
    for eps, sigma, m in sweep_results:
        acc = f"{m['binary_accuracy'] * 100:.2f}%"
        f1 = f"{m['f1_macro'] * 100:.2f}%"
        mcc = f"{m['binary_mcc']:.4f}"
        print(f"{eps:<12.2f}{sigma:<14.4f}{acc:<14}{f1:<12}{mcc:<10}")
    print("-" * 62 + "\n")


if __name__ == "__main__":
    main()
