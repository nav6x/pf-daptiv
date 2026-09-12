"""
Real-dataset benchmark runner.

Unlike scripts/benchmark_baselines.py (which trains only on
generate_synthetic_corpus), this script loads actual downloaded benchmark
CSVs (UNSW-NB15, CSE-CIC-IDS2018) through the existing src/data/parsers/,
and reports metrics that are genuinely measured -- not narrated.

Usage:
    python scripts/run_real_benchmark.py --dataset unsw_nb15
    python scripts/run_real_benchmark.py --dataset cicids2018
"""
import os
import sys
import json
import time
import argparse

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.dataset_loader import CDFVDataset
from src.data.parsers import parse_cicids2018, parse_unsw_nb15, parse_edge_iiotset, parse_dapt2020
from src.models.cnn1d import APTClassifier1DCNN
from src.models.baselines import get_random_forest_baseline
from src.federated.privacy import DifferentialPrivacyManager
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer
from src.utils.metrics import evaluate_predictions

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)


def stratified_cap(df: pd.DataFrame, label_col: str, cap: int, seed: int = SEED) -> pd.DataFrame:
    if len(df) <= cap:
        return df
    frac = cap / len(df)
    # NOTE: pandas>=2.2 groupby().apply() drops the grouping column from each
    # group, so iterate manually instead -- .apply() silently produced a
    # DataFrame missing `label_col`, which corrupted downstream label parsing.
    parts = [
        g.sample(max(1, int(round(len(g) * frac))), random_state=seed)
        for _, g in df.groupby(label_col)
    ]
    return pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)


def load_unsw_nb15(data_dir: str, cap: int):
    path = os.path.join(data_dir, "unsw_nb15", "training-set.csv")
    df = pd.read_csv(path)
    df = stratified_cap(df, "attack_cat", cap)
    x, y = parse_unsw_nb15(df)
    return x, y, len(df), path


def load_cicids2018(data_dir: str, cap: int):
    # The AWS-hosted CSE-CIC-IDS2018 CSVs use abbreviated CICFlowMeter column
    # names that don't match src/data/parsers/cicids2018.py's expected labels
    # (which follow the older/Kaggle-mirror full-word convention). Without
    # this alias map, most CDFV feature slots would silently zero-fill.
    COLUMN_ALIASES = {
        "Flow Pkts/s": "Flow Packets/s",
        "Bwd Pkts/s": "Bwd Packets/s",
        "Pkt Len Mean": "Packet Length Mean",
        "Pkt Len Var": "Packet Length Variance",
        "SYN Flag Cnt": "SYN Flag Count",
        "RST Flag Cnt": "RST Flag Count",
    }

    root = os.path.join(data_dir, "cicids2018")
    files = sorted(os.listdir(root))
    frames = []
    for f in files:
        if not f.endswith(".csv"):
            continue
        d = pd.read_csv(os.path.join(root, f), low_memory=False)
        d.columns = [c.strip() for c in d.columns]
        d = d.rename(columns=COLUMN_ALIASES)
        d = d[d["Label"] != "Label"]  # header rows re-embedded in some CIC CSVs
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["Label"])
    df = stratified_cap(df, "Label", cap)
    x, y = parse_cicids2018(df)
    return x, y, len(df), files


def load_edge_iiotset(data_dir: str, cap: int):
    # This Kaggle mirror's ML-ready CSV omits a couple of Wireshark fields the
    # parser expects (tcp.flags.syn/reset, frame.len, tcp.time_delta) but has
    # direct equivalents under different names for two of them.
    COLUMN_ALIASES = {
        "tcp.connection.syn": "tcp.flags.syn",
        "tcp.connection.rst": "tcp.flags.reset",
    }
    path = os.path.join(data_dir, "edge_iiotset", "ML-EdgeIIoT-dataset.csv")
    df = pd.read_csv(path, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns=COLUMN_ALIASES)
    df = df.dropna(subset=["Attack_type"])
    df = stratified_cap(df, "Attack_type", cap)
    x, y = parse_edge_iiotset(df)
    return x, y, len(df), path


def load_dapt2020(data_dir: str, cap: int):
    root = os.path.join(data_dir, "dapt2020", "csv")
    frames = []
    skipped = []
    for f in sorted(os.listdir(root)):
        if not f.endswith(".csv"):
            continue
        d = pd.read_csv(os.path.join(root, f), low_memory=False)
        d.columns = [c.strip() for c in d.columns]
        if "Stage" not in d.columns:
            # e.g. enp0s3-pvt-thursday.pcap_Flow.csv ships with no header row
            # at all, so pandas silently treats its first data row as columns.
            skipped.append(f)
            continue
        d["Stage"] = d["Stage"].astype(str).str.strip().replace({"BENIGN": "Benign"})
        frames.append(d)
    if skipped:
        print(f"Skipped malformed DAPT2020 file(s) (no Stage column): {skipped}")
    df = pd.concat(frames, ignore_index=True)
    df = stratified_cap(df, "Stage", cap)
    x, y = parse_dapt2020(df)
    return x, y, len(df), [f for f in sorted(os.listdir(root)) if f.endswith(".csv") and f not in skipped]


def train_test_split_np(x, y, test_frac=0.2, seed=SEED):
    rng = np.random.RandomState(seed)
    idx = rng.permutation(len(x))
    n_test = int(len(x) * test_frac)
    test_idx, train_idx = idx[:n_test], idx[n_test:]
    return x[train_idx], y[train_idx], x[test_idx], y[test_idx]


def partition_clients(x, y, num_clients, seed=SEED):
    rng = np.random.RandomState(seed)
    idx = rng.permutation(len(x))
    return [(x[s], y[s]) for s in np.array_split(idx, num_clients)]


def run_federated(x_train, y_train, x_test, y_test, epsilon, rounds, num_clients, local_epochs, device):
    dp = DifferentialPrivacyManager(epsilon=epsilon, delta=1e-5, clip_threshold=1.0, dual_layer=(epsilon > 0))
    parts = partition_clients(x_train, y_train, num_clients)

    def model_fn():
        return APTClassifier1DCNN(input_dim=35, num_classes=7)

    clients = [
        FederatedClient(i, CDFVDataset(px, py), model_fn, dp, local_epochs=local_epochs, batch_size=128, device=device)
        for i, (px, py) in enumerate(parts)
    ]
    test_ds = CDFVDataset(x_test, y_test)
    server = FederatedServer(model_fn(), clients, dp, test_ds, device=device)

    loss_history = []
    t0 = time.time()
    for r in range(1, rounds + 1):
        loss, _ = server.run_round(r)
        loss_history.append(loss)
    elapsed = time.time() - t0

    final_metrics = server.evaluate()
    final_metrics["_elapsed_sec"] = elapsed
    final_metrics["_loss_history"] = loss_history
    return final_metrics


def run_centralized_rf(x_train, y_train, x_test, y_test):
    rf = get_random_forest_baseline()
    t0 = time.time()
    rf.fit(x_train, y_train)
    elapsed = time.time() - t0
    preds = rf.predict(x_test)
    metrics = evaluate_predictions(y_test, preds, preds)  # probs unused by evaluate_predictions
    metrics["_elapsed_sec"] = elapsed
    return metrics


def run_centralized_cnn(x_train, y_train, x_test, y_test, epochs, device):
    model = APTClassifier1DCNN(input_dim=35, num_classes=7).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = torch.nn.CrossEntropyLoss()

    train_ds = CDFVDataset(x_train, y_train)
    test_ds = CDFVDataset(x_test, y_test)
    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=128, shuffle=True)
    test_loader = torch.utils.data.DataLoader(test_ds, batch_size=256, shuffle=False)

    t0 = time.time()
    model.train()
    for _ in range(epochs):
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            optimizer.step()
    elapsed = time.time() - t0

    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for bx, by in test_loader:
            bx = bx.to(device)
            preds = torch.argmax(model(bx), dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(by.numpy())

    metrics = evaluate_predictions(all_targets, all_preds, all_preds)
    metrics["_elapsed_sec"] = elapsed
    return metrics


def summarize(name, metrics):
    print(f"\n=== {name} ===")
    print(f"  binary_accuracy : {metrics['binary_accuracy']*100:.2f}%")
    print(f"  binary_precision: {metrics['binary_precision']*100:.2f}%")
    print(f"  binary_recall   : {metrics['binary_recall']*100:.2f}%")
    print(f"  binary_f1       : {metrics['binary_f1']*100:.2f}%")
    print(f"  binary_mcc      : {metrics['binary_mcc']:.4f}")
    print(f"  multi_accuracy  : {metrics['multi_accuracy']*100:.2f}%")
    print(f"  f1_macro        : {metrics['f1_macro']*100:.2f}%")
    print(f"  elapsed_sec     : {metrics.get('_elapsed_sec', 0):.1f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["unsw_nb15", "cicids2018", "edge_iiotset", "dapt2020"], required=True)
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    parser.add_argument("--cap", type=int, default=80000, help="Max rows after stratified subsampling")
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--clients", type=int, default=3)
    parser.add_argument("--local-epochs", type=int, default=1)
    parser.add_argument("--cnn-epochs", type=int, default=4)
    parser.add_argument("--epsilon", type=float, default=1.0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    device = "cpu"

    loaders = {
        "unsw_nb15": load_unsw_nb15,
        "cicids2018": load_cicids2018,
        "edge_iiotset": load_edge_iiotset,
        "dapt2020": load_dapt2020,
    }
    x, y, n_rows, source = loaders[args.dataset](args.data_dir, args.cap)

    x_train, y_train, x_test, y_test = train_test_split_np(x, y)

    print(f"Dataset: {args.dataset}")
    print(f"Source file(s): {source}")
    print(f"Rows used (after stratified cap={args.cap}): {n_rows}")
    print(f"Train: {len(x_train)}  Test: {len(x_test)}")
    print(f"Label distribution (train): {dict(zip(*np.unique(y_train, return_counts=True)))}")

    results = {
        "dataset": args.dataset,
        "source": str(source),
        "n_rows_used": int(n_rows),
        "n_train": int(len(x_train)),
        "n_test": int(len(x_test)),
        "cap": args.cap,
        "rounds": args.rounds,
        "clients": args.clients,
        "local_epochs": args.local_epochs,
        "epsilon": args.epsilon,
    }

    m = run_centralized_rf(x_train, y_train, x_test, y_test)
    summarize("Random Forest (centralized)", m)
    results["random_forest"] = m

    m = run_centralized_cnn(x_train, y_train, x_test, y_test, args.cnn_epochs, device)
    summarize("1D-CNN (centralized, upper bound)", m)
    results["centralized_cnn"] = m

    m = run_federated(x_train, y_train, x_test, y_test, 0.0, args.rounds, args.clients, args.local_epochs, device)
    summarize("FedAvg (no DP)", m)
    results["fedavg_no_dp"] = m

    m = run_federated(x_train, y_train, x_test, y_test, args.epsilon, args.rounds, args.clients, args.local_epochs, device)
    summarize(f"PF-DAPTIV (epsilon={args.epsilon})", m)
    results["pf_daptiv"] = m

    out_path = args.out or f"results_{args.dataset}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved results to {out_path}")


if __name__ == "__main__":
    main()
