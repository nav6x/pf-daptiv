import numpy as np
import pandas as pd
from typing import Tuple
from ..cdfv_schema import get_feature_index

CICIDS2018_LABEL_MAP = {
    "Benign": 0,
    "FTP-BruteForce": 2,
    "SSH-Bruteforce": 2,
    "DoS attacks-GoldenEye": 2,
    "DoS attacks-Slowloris": 2,
    "DoS attacks-SlowHTTPTest": 2,
    "DoS attacks-Hulk": 2,
    "Brute Force -Web": 2,
    "Brute Force -XSS": 2,
    "SQL Injection": 2,
    "Infiltration": 4,
    "Bot": 3,
    "DDOS attack-HOIC": 2,
    "DDOS attack-LOIC-UDP": 2,
}


def parse_cicids2018(df_or_path, max_rows: int = None) -> Tuple[np.ndarray, np.ndarray]:
    if isinstance(df_or_path, str):
        df = pd.read_csv(df_or_path, nrows=max_rows)
    else:
        df = df_or_path.head(max_rows) if max_rows else df_or_path.copy()

    n_samples = len(df)
    cdfv_matrix = np.zeros((n_samples, 35), dtype=np.float32)

    df.columns = [c.strip() for c in df.columns]

    def get_scaled(col_name: str, default=0.0):
        if col_name in df.columns:
            vals = pd.to_numeric(df[col_name], errors="coerce").fillna(default).values
            min_v, max_v = np.min(vals), np.max(vals)
            if max_v > min_v:
                return (vals - min_v) / (max_v - min_v)
            return np.zeros_like(vals)
        return np.full(n_samples, default, dtype=np.float32)

    cdfv_matrix[:, get_feature_index("flow_duration")] = get_scaled("Flow Duration")
    cdfv_matrix[:, get_feature_index("fwd_pkts_per_sec")] = get_scaled("Flow Packets/s")
    cdfv_matrix[:, get_feature_index("bwd_pkts_per_sec")] = get_scaled("Bwd Packets/s")
    cdfv_matrix[:, get_feature_index("flow_iat_mean")] = get_scaled("Flow IAT Mean")
    cdfv_matrix[:, get_feature_index("flow_iat_std")] = get_scaled("Flow IAT Std")

    cdfv_matrix[:, get_feature_index("pkt_len_mean")] = get_scaled("Packet Length Mean")
    cdfv_matrix[:, get_feature_index("pkt_len_var")] = get_scaled("Packet Length Variance")
    cdfv_matrix[:, get_feature_index("syn_flag_cnt")] = get_scaled("SYN Flag Count")
    cdfv_matrix[:, get_feature_index("rst_flag_cnt")] = get_scaled("RST Flag Count")

    cdfv_matrix[:, get_feature_index("pdi")] = get_scaled("Dst Port")
    cdfv_matrix[:, get_feature_index("er")] = get_scaled("Down/Up Ratio")
    cdfv_matrix[:, get_feature_index("bcv")] = get_scaled("Flow IAT Min")

    label_col = "Label" if "Label" in df.columns else df.columns[-1]
    raw_labels = df[label_col].astype(str).str.strip()
    y_stages = np.array([CICIDS2018_LABEL_MAP.get(lbl, 0) for lbl in raw_labels], dtype=np.int64)

    return cdfv_matrix, y_stages

