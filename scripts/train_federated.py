
import os
import sys
import argparse
import yaml

import torch
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.synthetic_apt import generate_synthetic_corpus, partition_data_across_clients
from src.data.dataset_loader import CDFVDataset, apply_local_smote
from src.models.cnn1d import APTClassifier1DCNN
from src.federated.privacy import DifferentialPrivacyManager
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer




def parse_args():
    parser = argparse.ArgumentParser(description="PF-DAPTIV federated training")
    parser.add_argument("--config", type=str, default="config/default_config.yaml", help="Path to YAML config")
    parser.add_argument("--rounds", type=int, default=None, help="Communication rounds")
    parser.add_argument("--clients", type=int, default=None, help="Number of client nodes")
    parser.add_argument("--local-epochs", type=int, default=None, help="Local epochs per round")
    parser.add_argument("--epsilon", type=float, default=None, help="Privacy budget epsilon")
    parser.add_argument("--delta", type=float, default=None, help="Privacy parameter delta")
    parser.add_argument("--clip", type=float, default=None, help="L2 gradient clipping threshold C")
    parser.add_argument("--samples", type=int, default=6000, help="Synthetic telemetry samples")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--save-model", type=str, default="checkpoints/global_model.pt")
    return parser.parse_args()


def load_config(config_path: str):
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def main():
    args = parse_args()
    config = load_config(args.config)

    fed_cfg = config.get("federated", {})
    model_cfg = config.get("model", {})
    priv_cfg = config.get("privacy", {})

    rounds = args.rounds or fed_cfg.get("rounds", 15)
    num_clients = args.clients or fed_cfg.get("num_clients", 6)
    local_epochs = args.local_epochs or fed_cfg.get("local_epochs", 5)
    batch_size = fed_cfg.get("batch_size", 64)
    lr = fed_cfg.get("learning_rate", 0.001)

    epsilon = args.epsilon if args.epsilon is not None else priv_cfg.get("epsilon", 1.0)
    delta = args.delta if args.delta is not None else priv_cfg.get("delta", 1e-5)
    clip_threshold = args.clip if args.clip is not None else priv_cfg.get("clip_threshold", 1.0)
    dual_layer = priv_cfg.get("dual_layer_noise", True)

    print("[*] initializing run: %d rounds, %d clients, %d local epochs" % (rounds, num_clients, local_epochs))
    print("[*] privacy: eps=%.2f, delta=%s, clip=%.2f, dual_layer=%s" % (epsilon, delta, clip_threshold, dual_layer))
    print("[*] device: %s" % args.device)

    df, y_multi, _ = generate_synthetic_corpus(total_samples=args.samples, random_state=42)
    x_raw = df.values

    split_idx = int(len(x_raw) * 0.8)
    x_train_pool, x_test = x_raw[:split_idx], x_raw[split_idx:]
    y_train_pool, y_test = y_multi[:split_idx], y_multi[split_idx:]

    test_dataset = CDFVDataset(x_test, y_test)
    client_data_partitions = partition_data_across_clients(
        x_train_pool, y_train_pool, num_clients=num_clients
    )

    dp_manager = DifferentialPrivacyManager(
        epsilon=epsilon,
        delta=delta,
        clip_threshold=clip_threshold,
        dual_layer=dual_layer,
    )

    def create_model():
        return APTClassifier1DCNN(
            input_dim=model_cfg.get("input_dim", 35),
            conv1_filters=model_cfg.get("conv1_filters", 64),
            conv1_kernel=model_cfg.get("conv1_kernel", 3),
            conv2_filters=model_cfg.get("conv2_filters", 128),
            conv2_kernel=model_cfg.get("conv2_kernel", 3),
            pool_size=model_cfg.get("pool_size", 2),
            dense_units=model_cfg.get("dense_units", 64),
            dropout_rate=model_cfg.get("dropout_rate", 0.4),
            num_classes=model_cfg.get("num_classes", 7),
        )

    clients = []
    for c_id, (cx, cy) in enumerate(client_data_partitions):
        cx_bal, cy_bal = apply_local_smote(cx, cy, target_apt_ratio=0.33)
        client = FederatedClient(
            client_id=c_id,
            dataset=CDFVDataset(cx_bal, cy_bal),
            model_fn=create_model,
            dp_manager=dp_manager,
            batch_size=batch_size,
            local_epochs=local_epochs,
            lr=lr,
            device=args.device,
        )
        clients.append(client)

    global_model = create_model()
    server = FederatedServer(
        global_model=global_model,
        clients=clients,
        dp_manager=dp_manager,
        test_dataset=test_dataset,
        device=args.device,
    )

    print("[*] starting federated training loop...")
    for r in range(1, rounds + 1):
        loss, metrics = server.run_round(r)
        print(
            "[+] round %02d/%02d - loss: %.4f | acc: %5.2f%% | prec: %5.2f%% | rec: %5.2f%% | f1: %5.2f%%"
            % (
                r,
                rounds,
                loss,
                metrics["binary_accuracy"] * 100,
                metrics["binary_precision"] * 100,
                metrics["binary_recall"] * 100,
                metrics["f1_macro"] * 100,
            )
        )

    final_metrics = server.evaluate()
    print("\n[+] evaluation complete:")
    print("    binary accuracy: %.2f%%" % (final_metrics["binary_accuracy"] * 100))
    print("    precision:       %.2f%%" % (final_metrics["binary_precision"] * 100))
    print("    recall:          %.2f%%" % (final_metrics["binary_recall"] * 100))
    print("    macro-f1:        %.2f%%" % (final_metrics["binary_f1"] * 100))
    print("    mcc:             %.4f" % final_metrics["binary_mcc"])
    print("    multi-class acc: %.2f%%" % (final_metrics["multi_accuracy"] * 100))

    os.makedirs(os.path.dirname(args.save_model) or ".", exist_ok=True)
    torch.save(server.global_model.state_dict(), args.save_model)
    print("[+] saved global model checkpoint to %s\n" % args.save_model)


if __name__ == "__main__":
    main()
