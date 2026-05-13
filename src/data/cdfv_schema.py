from typing import List, Dict

APT_STAGES: Dict[int, str] = {
    0: "Benign",
    1: "S1: Reconnaissance",
    2: "S2: Initial Compromise",
    3: "S3: Foothold Establishment",
    4: "S4: Lateral Movement",
    5: "S5: Data Exfiltration",
    6: "S6: Post-Exfiltration Persistence",
}

CDFV_CATEGORIES = {
    "Flow Statistics": [
        "flow_duration",
        "fwd_pkts_per_sec",
        "bwd_pkts_per_sec",
        "flow_iat_mean",
        "flow_iat_std",
    ],
    "Lateral Movement Indicators": [
        "ct_dst_src_ltm",
        "ct_srv_src",
        "ct_dst_ltm",
        "ct_src_ltm",
    ],
    "Packet-Level Features": [
        "tcp_ack_raw",
        "pkt_len_mean",
        "pkt_len_var",
        "syn_flag_cnt",
        "rst_flag_cnt",
    ],
    "Protocol and Service Features": [
        "mqtt_msgtype",
        "proto_type",
        "service_type",
        "tcp_state",
        "header_len_ratio",
    ],
    "APT Behavioural Features": [
        "c2_interval",
        "beacon_rate",
        "dns_query_len",
        "payload_ratio",
        "failed_conn_ratio",
    ],
    "Host Behavioural Features": [
        "proc_creation_rate",
        "auth_fail_cnt",
        "privilege_escalation_flag",
        "file_mod_rate",
        "registry_writes",
    ],
    "Derived Behavioural Metrics": [
        "pdi",
        "bcv",
        "pe",
        "lhc",
        "er",
        "dt",
    ],
}

CDFV_FEATURE_NAMES: List[str] = [
    "flow_duration",
    "fwd_pkts_per_sec",
    "bwd_pkts_per_sec",
    "flow_iat_mean",
    "flow_iat_std",
    "ct_dst_src_ltm",
    "ct_srv_src",
    "ct_dst_ltm",
    "ct_src_ltm",
    "tcp_ack_raw",
    "pkt_len_mean",
    "pkt_len_var",
    "syn_flag_cnt",
    "rst_flag_cnt",
    "mqtt_msgtype",
    "proto_type",
    "service_type",
    "tcp_state",
    "header_len_ratio",
    "c2_interval",
    "beacon_rate",
    "dns_query_len",
    "payload_ratio",
    "failed_conn_ratio",
    "proc_creation_rate",
    "auth_fail_cnt",
    "privilege_escalation_flag",
    "file_mod_rate",
    "registry_writes",
    "pdi",
    "bcv",
    "pe",
    "lhc",
    "er",
    "dt",
]

assert len(CDFV_FEATURE_NAMES) == 35, f"Expected 35 features, got {len(CDFV_FEATURE_NAMES)}"


def get_feature_index(feature_name: str) -> int:
    return CDFV_FEATURE_NAMES.index(feature_name)


def get_category_for_feature(feature_name: str) -> str:
    for category, features in CDFV_CATEGORIES.items():
        if feature_name in features:
            return category
    return "Unknown"
