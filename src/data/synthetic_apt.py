from typing import Tuple, List
import numpy as np
import pandas as pd

from .cdfv_schema import CDFV_FEATURE_NAMES, get_feature_index


def generate_stage_features(
    stage: int, n_samples: int, noise_scale: float = 0.08
) -> np.ndarray:
    features = np.zeros((n_samples, 35), dtype=np.float32)

    features += np.random.uniform(0.02, 0.15, size=(n_samples, 35))

    if stage == 0:
        features[:, get_feature_index("flow_duration")] = np.random.uniform(0.1, 0.4, n_samples)
        features[:, get_feature_index("pkt_len_mean")] = np.random.uniform(0.2, 0.5, n_samples)
        features[:, get_feature_index("bcv")] = np.random.uniform(0.7, 0.95, n_samples)
        features[:, get_feature_index("pe")] = np.random.uniform(0.2, 0.4, n_samples)

    elif stage == 1:
        features[:, get_feature_index("pdi")] = np.random.uniform(0.75, 0.98, n_samples)
        features[:, get_feature_index("syn_flag_cnt")] = np.random.uniform(0.7, 0.95, n_samples)
        features[:, get_feature_index("ct_dst_ltm")] = np.random.uniform(0.65, 0.90, n_samples)
        features[:, get_feature_index("fwd_pkts_per_sec")] = np.random.uniform(0.6, 0.85, n_samples)
        features[:, get_feature_index("dt")] = np.random.uniform(0.05, 0.2, n_samples)

    elif stage == 2:
        features[:, get_feature_index("auth_fail_cnt")] = np.random.uniform(0.6, 0.92, n_samples)
        features[:, get_feature_index("mqtt_msgtype")] = np.random.uniform(0.7, 0.95, n_samples)
        features[:, get_feature_index("pe")] = np.random.uniform(0.65, 0.88, n_samples)
        features[:, get_feature_index("pkt_len_var")] = np.random.uniform(0.5, 0.8, n_samples)
        features[:, get_feature_index("failed_conn_ratio")] = np.random.uniform(0.6, 0.85, n_samples)

    elif stage == 3:
        features[:, get_feature_index("proc_creation_rate")] = np.random.uniform(0.7, 0.95, n_samples)
        features[:, get_feature_index("privilege_escalation_flag")] = np.random.choice(
            [0.0, 1.0], size=n_samples, p=[0.2, 0.8]
        )
        features[:, get_feature_index("beacon_rate")] = np.random.uniform(0.6, 0.9, n_samples)
        features[:, get_feature_index("bcv")] = np.random.uniform(0.1, 0.35, n_samples)
        features[:, get_feature_index("c2_interval")] = np.random.uniform(0.5, 0.8, n_samples)

    elif stage == 4:
        features[:, get_feature_index("lhc")] = np.random.uniform(0.7, 0.98, n_samples)
        features[:, get_feature_index("ct_dst_src_ltm")] = np.random.uniform(0.75, 0.95, n_samples)
        features[:, get_feature_index("ct_srv_src")] = np.random.uniform(0.7, 0.92, n_samples)
        features[:, get_feature_index("ct_src_ltm")] = np.random.uniform(0.65, 0.9, n_samples)
        features[:, get_feature_index("dt")] = np.random.uniform(0.4, 0.7, n_samples)

    elif stage == 5:
        features[:, get_feature_index("er")] = np.random.uniform(0.75, 0.98, n_samples)
        features[:, get_feature_index("payload_ratio")] = np.random.uniform(0.7, 0.95, n_samples)
        features[:, get_feature_index("bwd_pkts_per_sec")] = np.random.uniform(0.65, 0.92, n_samples)
        features[:, get_feature_index("dns_query_len")] = np.random.uniform(0.7, 0.95, n_samples)
        features[:, get_feature_index("pe")] = np.random.uniform(0.75, 0.99, n_samples)
        features[:, get_feature_index("dt")] = np.random.uniform(0.6, 0.9, n_samples)

    elif stage == 6:
        features[:, get_feature_index("file_mod_rate")] = np.random.uniform(0.75, 0.95, n_samples)
        features[:, get_feature_index("registry_writes")] = np.random.uniform(0.7, 0.92, n_samples)
        features[:, get_feature_index("dt")] = np.random.uniform(0.85, 1.0, n_samples)
        features[:, get_feature_index("bcv")] = np.random.uniform(0.1, 0.3, n_samples)

    jitter = np.random.normal(0, noise_scale, size=features.shape)
    return np.clip(features + jitter, 0.0, 1.0)


def generate_synthetic_corpus(
    total_samples: int = 12000,
    apt_ratio: float = 0.25,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    np.random.seed(random_state)

    n_apt = int(total_samples * apt_ratio)
    n_benign = total_samples - n_apt

    x_benign = generate_stage_features(stage=0, n_samples=n_benign)
    y_benign = np.zeros(n_benign, dtype=np.int64)

    stage_counts = [n_apt // 6] * 6
    stage_counts[-1] += n_apt - sum(stage_counts)

    x_stages = []
    y_stages = []
    for s_idx, count in enumerate(stage_counts, start=1):
        x_stages.append(generate_stage_features(stage=s_idx, n_samples=count))
        y_stages.append(np.full(count, s_idx, dtype=np.int64))

    x_all = np.vstack([x_benign] + x_stages)
    y_multi = np.concatenate([y_benign] + y_stages)
    y_binary = (y_multi > 0).astype(np.int64)

    indices = np.random.permutation(len(y_multi))
    x_all = x_all[indices]
    y_multi = y_multi[indices]
    y_binary = y_binary[indices]

    df = pd.DataFrame(x_all, columns=CDFV_FEATURE_NAMES)
    return df, y_multi, y_binary


def partition_data_across_clients(
    x: np.ndarray,
    y: np.ndarray,
    num_clients: int = 6,
    non_iid_alpha: float = 1.0,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    num_classes = len(np.unique(y))
    client_indices = [[] for _ in range(num_clients)]

    for c in range(num_classes):
        idx_c = np.where(y == c)[0]
        np.random.shuffle(idx_c)
        proportions = np.random.dirichlet(np.repeat(non_iid_alpha, num_clients))
        proportions = (np.cumsum(proportions) * len(idx_c)).astype(int)[:-1]
        splits = np.split(idx_c, proportions)
        for i, split in enumerate(splits):
            client_indices[i].extend(split)

    client_partitions = []
    for indices in client_indices:
        np.random.shuffle(indices)
        client_partitions.append((x[indices], y[indices]))

    return client_partitions
