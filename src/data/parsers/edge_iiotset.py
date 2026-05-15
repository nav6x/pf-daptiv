import numpy as np
import pandas as pd
from typing import Tuple
from ..cdfv_schema import get_feature_index

EDGE_IIOT_LABEL_MAP = {
    "Normal": 0,
    "Scanning": 1,
    "Fingerprinting": 1,
    "Vulnerability_scanner": 1,
    "SQL_injection": 2,
    "Command_injection": 2,
    "Backdoor_malware": 3,
    "MITM": 4,
    "Ransomware": 5,
    "DDoS_HTTP": 2,
    "DDoS_TCP": 2,
    "DDoS_UDP": 2,
}


def parse_edge_iiotset(df_or_path, max_rows: int = None) -> Tuple[np.ndarray, np.ndarray]:
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

    cdfv_matrix[:, get_feature_index("tcp_ack_raw")] = get_scaled("tcp.ack_raw")
    cdfv_matrix[:, get_feature_index("mqtt_msgtype")] = get_scaled("mqtt.msgtype")
    cdfv_matrix[:, get_feature_index("syn_flag_cnt")] = get_scaled("tcp.flags.syn")
    cdfv_matrix[:, get_feature_index("rst_flag_cnt")] = get_scaled("tcp.flags.reset")
    cdfv_matrix[:, get_feature_index("pkt_len_mean")] = get_scaled("frame.len")
    cdfv_matrix[:, get_feature_index("flow_duration")] = get_scaled("tcp.time_delta")

    cdfv_matrix[:, get_feature_index("pe")] = get_scaled("tcp.payload")
    cdfv_matrix[:, get_feature_index("pdi")] = get_scaled("tcp.dstport")
    cdfv_matrix[:, get_feature_index("bcv")] = get_scaled("mqtt.topic_len")

    label_col = "Attack_type" if "Attack_type" in df.columns else "label"
    raw_labels = df[label_col].astype(str).str.strip()
    y_stages = np.array([EDGE_IIOT_LABEL_MAP.get(lbl, 0) for lbl in raw_labels], dtype=np.int64)

    return cdfv_matrix, y_stages

