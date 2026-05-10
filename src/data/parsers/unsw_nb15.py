import numpy as np
import pandas as pd
from typing import Tuple
from ..cdfv_schema import get_feature_index

UNSW_LABEL_MAP = {
    "Normal": 0,
    "Reconnaissance": 1,
    "Exploits": 2,
    "Backdoor": 3,
    "Shellcode": 3,
    "Generic": 4,
    "Analysis": 5,
    "Fuzzers": 2,
    "DoS": 2,
    "Worms": 4,
}


def parse_unsw_nb15(df_or_path, max_rows: int = None) -> Tuple[np.ndarray, np.ndarray]:
    if isinstance(df_or_path, str):
        df = pd.read_csv(df_or_path, nrows=max_rows)
    else:
        df = df_or_path.head(max_rows) if max_rows else df_or_path.copy()

    n_samples = len(df)
    cdfv_matrix = np.zeros((n_samples, 35), dtype=np.float32)

    df.columns = [c.strip().lower() for c in df.columns]

    def get_scaled(col_name: str, default=0.0):
        if col_name in df.columns:
            vals = pd.to_numeric(df[col_name], errors="coerce").fillna(default).values
            min_v, max_v = np.min(vals), np.max(vals)
            if max_v > min_v:
                return (vals - min_v) / (max_v - min_v)
            return np.zeros_like(vals)
        return np.full(n_samples, default, dtype=np.float32)

    cdfv_matrix[:, get_feature_index("flow_duration")] = get_scaled("dur")
    cdfv_matrix[:, get_feature_index("fwd_pkts_per_sec")] = get_scaled("spkts")
    cdfv_matrix[:, get_feature_index("bwd_pkts_per_sec")] = get_scaled("dpkts")

    cdfv_matrix[:, get_feature_index("ct_dst_src_ltm")] = get_scaled("ct_dst_src_ltm")
    cdfv_matrix[:, get_feature_index("ct_srv_src")] = get_scaled("ct_srv_src")
    cdfv_matrix[:, get_feature_index("ct_dst_ltm")] = get_scaled("ct_dst_ltm")
    cdfv_matrix[:, get_feature_index("ct_src_ltm")] = get_scaled("ct_src_ltm")

    cdfv_matrix[:, get_feature_index("pkt_len_mean")] = get_scaled("sbytes")
    cdfv_matrix[:, get_feature_index("rst_flag_cnt")] = get_scaled("dbytes")

    cdfv_matrix[:, get_feature_index("lhc")] = get_scaled("ct_dst_src_ltm")
    cdfv_matrix[:, get_feature_index("er")] = get_scaled("rate")
    cdfv_matrix[:, get_feature_index("pe")] = get_scaled("sjit")

    label_col = "attack_cat" if "attack_cat" in df.columns else "label"
    raw_labels = df[label_col].astype(str).str.strip()
    y_stages = np.array([UNSW_LABEL_MAP.get(lbl, 0) for lbl in raw_labels], dtype=np.int64)

    return cdfv_matrix, y_stages

