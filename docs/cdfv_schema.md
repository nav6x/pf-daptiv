# Canonical Distributed Feature Vector (CDFV) Reference Specification

---

## 1. Specification Overview

The Canonical Distributed Feature Vector (CDFV) is an immutable 35-dimensional schema that provides a unified interface for industrial IoT and enterprise network telemetry.

![CDFV Feature Vector Structure](../assets/cdfv_feature_vector.png)

---

## 2. Normalization Formulation

Raw values are scaled to the unit interval $[0.0, 1.0]$ using min-max normalization with boundary clipping:

$$
x_i = \text{clip}\left( \frac{v_i - v_{\min, i}}{v_{\max, i} - v_{\min, i}}, 0.0, 1.0 \right)
$$

---

## 3. The 35 Feature Definitions

| Index | Symbol | Name | Physical Unit | Domain Group |
|---|---|---|---|---|
| 0 | $\Delta t_{\text{flow}}$ | `flow_duration` | Seconds ($s$) | Flow Dynamics |
| 1 | $N_{\text{fwd}}$ | `total_fwd_packets` | Count | Flow Dynamics |
| 2 | $N_{\text{bwd}}$ | `total_bwd_packets` | Count | Flow Dynamics |
| 3 | $V_{\text{fwd}}$ | `total_fwd_bytes` | Bytes | Flow Dynamics |
| 4 | $V_{\text{bwd}}$ | `total_bwd_bytes` | Bytes | Flow Dynamics |
| 5 | $L_{\text{fwd,max}}$ | `fwd_packet_len_max` | Bytes | Flow Dynamics |
| 6 | $L_{\text{fwd,min}}$ | `fwd_packet_len_min` | Bytes | Flow Dynamics |
| 7 | $\mu_{\text{pkt,len}}$ | `fwd_packet_len_mean` | Bytes | Flow Dynamics |
| 8 | $L_{\text{bwd,max}}$ | `bwd_packet_len_max` | Bytes | TCP Flags & State |
| 9 | $L_{\text{bwd,min}}$ | `bwd_packet_len_min` | Bytes | TCP Flags & State |
| 10 | $\mu_{\text{bwd,len}}$ | `bwd_packet_len_mean` | Bytes | TCP Flags & State |
| 11 | $\lambda_{\text{byte}}$ | `flow_bytes_per_sec` | Bytes/s | TCP Flags & State |
| 12 | $\lambda_{\text{pkt}}$ | `flow_packets_per_sec` | Packets/s | TCP Flags & State |
| 13 | $\mu_{\text{fwd,IAT}}$ | `fwd_iat_mean` | $\mu s$ | TCP Flags & State |
| 14 | $\sigma_{\text{fwd,IAT}}$ | `fwd_iat_std` | $\mu s$ | TCP Flags & State |
| 15 | $\mu_{\text{bwd,IAT}}$ | `bwd_iat_mean` | $\mu s$ | TCP Flags & State |
| 16 | $\sigma_{\text{bwd,IAT}}$ | `bwd_iat_std` | $\mu s$ | Payload Entropy |
| 17 | $c_{\text{SYN}}$ | `syn_flag_count` | Count | Payload Entropy |
| 18 | $c_{\text{FIN}}$ | `fin_flag_count` | Count | Payload Entropy |
| 19 | $c_{\text{RST}}$ | `rst_flag_count` | Count | Payload Entropy |
| 20 | $c_{\text{PSH}}$ | `psh_flag_count` | Count | Payload Entropy |
| 21 | $c_{\text{ACK}}$ | `ack_flag_count` | Count | Payload Entropy |
| 22 | $c_{\text{URG}}$ | `urg_flag_count` | Count | Payload Entropy |
| 23 | $r_{\text{down/up}}$ | `down_up_ratio` | Ratio | Payload Entropy |
| 24 | $\mu_{\text{pkt,size}}$ | `pkt_size_avg` | Bytes | Inter-Arrival Time |
| 25 | $W_{\text{init,fwd}}$ | `init_win_bytes_fwd` | Bytes | Inter-Arrival Time |
| 26 | $W_{\text{init,bwd}}$ | `init_win_bytes_bwd` | Bytes | Inter-Arrival Time |
| 27 | $\mu_{\text{active}}$ | `active_mean` | $\mu s$ | Inter-Arrival Time |
| 28 | $\mu_{\text{idle}}$ | `idle_mean` | $\mu s$ | Inter-Arrival Time |
| 29 | $H_{\text{src,port}}$ | `src_port_entropy` | Bits | Inter-Arrival Time |
| 30 | $H_{\text{dst,port}}$ | `dst_port_entropy` | Bits | Context & Protocol |
| 31 | $\lambda_{\text{DNS}}$ | `dns_query_rate` | Queries/s | Context & Protocol |
| 32 | $r_{\text{HTTP,err}}$ | `http_error_ratio` | Ratio | Context & Protocol |
| 33 | $r_{\text{Modbus,err}}$ | `modbus_exception_rate` | Ratio | Context & Protocol |
| 34 | $r_{\text{DNP3,abort}}$ | `dnp3_abort_rate` | Ratio | Context & Protocol |

---

## 4. APT Stage Label Mapping

![Threat Model & Multi-Stage APT Progression](../assets/threat_model_lifecycle.png)

- Label 0: Normal Operational Traffic
- Label 1: Reconnaissance (MITRE T1595, T1046)
- Label 2: Weaponization (MITRE T1587, T1204)
- Label 3: Delivery and Exploitation (MITRE T1190, T1210)
- Label 4: Installation and Foothold (MITRE T1543, T1053)
- Label 5: Command and Control (MITRE T1071, T1573)
- Label 6: Actions and Exfiltration (MITRE T1048, T1020)
