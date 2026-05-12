import numpy as np
import pandas as pd
from typing import Tuple
from ..cdfv_schema import get_feature_index

DAPT2020_LABEL_MAP = {
    "Benign": 0,
    "Reconnaissance": 1,
    "Establish Foothold": 2,
    "Lateral Movement": 4,
    "Data Exfiltration": 5,
}


def parse_dapt2020(df_or_path, max_rows: int = None) -> Tuple[np.ndarray, np.ndarray]:
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

    cdfv_matrix[:, get_feature_index("c2_interval")] = get_scaled("Flow IAT Mean")
    cdfv_matrix[:, get_feature_index("beacon_rate")] = get_scaled("Fwd Packets/s")
    cdfv_matrix[:, get_feature_index("dns_query_len")] = get_scaled("Packet Length Mean")
    cdfv_matrix[:, get_feature_index("payload_ratio")] = get_scaled("Down/Up Ratio")

    cdfv_matrix[:, get_feature_index("bcv")] = get_scaled("Flow IAT Std")
    cdfv_matrix[:, get_feature_index("pe")] = get_scaled("Packet Length Variance")
    cdfv_matrix[:, get_feature_index("er")] = get_scaled("Bwd Packets/s")

    label_col = "Stage" if "Stage" in df.columns else ("Label" if "Label" in df.columns else df.columns[-1])
    raw_labels = df[label_col].astype(str).str.strip()
    y_stages = np.array([DAPT2020_LABEL_MAP.get(lbl, 0) for lbl in raw_labels], dtype=np.int64)

    return cdfv_matrix, y_stages

