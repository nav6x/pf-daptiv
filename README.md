# PF-DAPTIV

### Privacy-Preserving Federated Detection of Advanced Persistent Threats in Industrial IoT and Critical Infrastructure Networks

---

## Table of Contents

- [System Overview](#system-overview)
- [System Architecture](#system-architecture)
- [Threat Model and Attack Progression](#threat-model-and-attack-progression)
- [Edge 1D-CNN Feature Extractor](#edge-1d-cnn-feature-extractor)
- [Canonical Distributed Feature Vector (CDFV)](#canonical-distributed-feature-vector-cdfv)
- [Federated Synchronization Protocol](#federated-synchronization-protocol)
- [Client-Side Differential Privacy Engine](#client-side-differential-privacy-engine)
- [Privacy Budget Tracking and Moments Accountant](#privacy-budget-tracking-and-moments-accountant)
- [Architectural Module Ablation Analysis](#architectural-module-ablation-analysis)
- [Benchmark Performance Evaluation](#benchmark-performance-evaluation)
- [Global Federated Convergence Dynamics](#global-federated-convergence-dynamics)
- [Multiclass ROC Discrimination](#multiclass-roc-discrimination)
- [Stage Classification Confusion Matrix](#stage-classification-confusion-matrix)
- [Feature Explainability (SHAP and CHIFS)](#feature-explainability-shap-and-chifs)
- [Privacy-Utility Pareto Frontier](#privacy-utility-pareto-frontier)
- [Quickstart Guide](#quickstart-guide)
- [Repository Structure](#repository-structure)
- [License](#license)

---

## System Overview

Industrial Internet of Things (IIoT) networks operate electrical grids, manufacturing facilities, chemical plants, water distribution systems, and transportation corridors. These networks face targeted cyberattacks known as Advanced Persistent Threats (APTs). Unlike random malware that executes immediate destructive routines, an APT is a prolonged campaign conducted by skilled adversaries who infiltrate a network, remain undetected for weeks or months, move across internal nodes, and alter physical machinery or extract confidential files without triggering basic alarms.

Securing industrial networks against APT campaigns presents two fundamental obstacles. First, industrial operators cannot share raw network telemetry with a central cloud platform. Network logs reveal internal topology, proprietary manufacturing parameters, and confidential communications. Data privacy laws also restrict transmitting critical infrastructure telemetry across jurisdictional boundaries. Second, industrial devices use diverse proprietary and open communication standards, creating mismatched log formats across facilities.

PF-DAPTIV resolves both obstacles through a decentralized, privacy-preserving framework. Edge sensor nodes train local threat detection models using raw telemetry that never leaves the local perimeter. Participating nodes share only mathematically masked model parameter updates with a central aggregation server. A calibrated Differential Privacy engine adds Gaussian perturbation to guarantee that attackers cannot reconstruct proprietary network flows from the shared parameters. In addition, a standardized 35-dimensional feature schema called the Canonical Distributed Feature Vector (CDFV) normalizes heterogeneous network logs into a uniform format across all edge devices.

---

## System Architecture

The following diagram illustrates the interaction between distributed edge sensor nodes and the central coordinator during a federated training cycle:

![PF-DAPTIV System Pipeline](assets/system_pipeline.png)

Each edge sensor node captures raw packets, flow summaries, and system logs from its local network perimeter. The node converts these inputs into normalized CDFV records and trains a local 1D-CNN model. Once training completes, the node computes the difference between its updated local parameters and the global checkpoint. It clips this parameter delta to a fixed sensitivity threshold and applies Gaussian differential privacy noise.

The central coordinator collects these perturbed deltas from all active clients. It aggregates the updates using sample-weighted Federated Averaging (FedAvg), updates the global model checkpoint, and broadcasts the new weights back to the edge clients. Raw network records remain within the local facility at every point in the process.

For an in-depth breakdown of communication sequences and error recovery policies, refer to [System Architecture](docs/architecture.md) and [Module 05: Federated Learning Protocol](docs/05_federated_learning_protocol.md).

---

## Threat Model and Attack Progression

Standard perimeter defenses focus on isolated intrusion events such as known file hashes or single malformed packets. APT campaigns avoid these indicators by executing low-and-slow operations that mirror normal administrative activity over long intervals:

![Multi-Stage APT Threat Model & Telemetry Mapping](assets/threat_model_lifecycle.png)

PF-DAPTIV maps the attack lifecycle to 6 distinct stages:

1. Reconnaissance: Adversaries discover active IP addresses, probe open ports, and gather service information.
2. Weaponization: Adversaries construct tailored exploit payloads and conceal them inside normal traffic flows or archive files.
3. Delivery and Exploit: Adversaries transmit malicious payloads to vulnerable services to gain an initial entry point.
4. Installation: Adversaries deploy persistent background tools, create administrative accounts, or modify system binaries.
5. Command and Control (C2): Compromised systems establish periodic outbound channels to receive instructions from the attacker.
6. Actions and Exfiltration: Adversaries gather sensitive system logs, process telemetry, or proprietary documents and transmit them outside the network.

To review how network flow measurements map to each stage of the attack progression, see [Module 02: Threat Model and APT Lifecycle](docs/02_threat_model_and_apt_lifecycle.md) and [Module 03: CDFV Telemetry Schema](docs/03_cdfv_telemetry_schema.md).

---

## Edge 1D-CNN Feature Extractor

Industrial edge gateways and programmable logic controllers have limited processing and memory budgets. The local detection engine uses a 1D Convolutional Neural Network designed for low computational overhead:

![1D-CNN Architecture](assets/cnn_architecture.png)

The neural network processes a 35-dimensional CDFV input vector through the following pipeline (**corrected to match the actual default arguments of `APTClassifier1DCNN` in `src/models/cnn1d.py`** -- the previous version of this section described filter counts, dropout rate, and output size that didn't match the real model class):

- Conv1D Layer 1: 64 filters, kernel size 3, stride 1, ReLU activation, and Batch Normalization.
- MaxPool1D Layer 1: Pool size 2, stride 2, condensing the representation from 35 to 17 features.
- Conv1D Layer 2: 128 filters, kernel size 3, stride 1, ReLU activation, and Batch Normalization.
- MaxPool1D Layer 2: Pool size 2, stride 2, condensing the representation from 17 to 8 features.
- Dense Layer: 64 units with ReLU activation and 40 percent dropout regularization.
- Output Layer: 7 units with Softmax activation, generating class probabilities across the 7 APT stages (`APT_STAGES` in `src/data/cdfv_schema.py` runs 0-6, including Benign).

Detailed mathematical dimensions and parameter counts are available in [Module 04: Edge 1D-CNN Architecture](docs/04_edge_1d_cnn_architecture.md) -- that document has the same corrections applied.

---

## Canonical Distributed Feature Vector (CDFV)

Network devices from separate vendors produce incompatible log formats. For example, routers emit NetFlow summaries, software monitors produce Zeek records, and industrial sensors emit Modbus frames. The CDFV converts these varied inputs into a single 35-dimensional vector:

![CDFV Feature Vector Structure](assets/cdfv_feature_vector.png)

The 35 features belong to 5 functional domains:

- Flow Dynamics (Positions 0 to 7): Connection length, forward packet counts, backward packet counts, forward byte totals, backward byte totals, and transmission rates.
- TCP Flags and State (Positions 8 to 15): SYN, FIN, RST, PSH, ACK, and URG flag counters, initial window sizes, and TCP state transitions.
- Payload Entropy (Positions 16 to 23): Shannon entropy of byte contents, mean payload length, payload variance, and header-to-payload ratios.
- Inter-Arrival Time (Positions 24 to 29): Forward and backward packet arrival spacing, maximum inter-arrival intervals, and timing jitter.
- Context and Protocol (Positions 30 to 34): Destination port categories, connection error ratios, time-to-live values, and industrial protocol anomaly rates.

Every value is scaled into the range [0.0, 1.0] using min-max normalization. Complete feature definitions and extraction logic are documented in [Module 03: CDFV Telemetry Schema](docs/03_cdfv_telemetry_schema.md) and [CDFV Schema Reference](docs/cdfv_schema.md).

---

## Federated Synchronization Protocol

The distributed training protocol coordinates edge clients and the central aggregator in synchronous rounds:

![Federated Round Synchronization Protocol](assets/client_server_protocol.png)

During round $t$:

1. The coordinator broadcasts global model checkpoint $w_t$ to all connected edge nodes.
2. Each client trains the model on its private dataset for a configured number of local epochs.
3. Each client calculates its local parameter update $\Delta w_k = w_k^{(t)} - w_t$.
4. The client limits the magnitude of its update using $L_2$ norm clipping: $\|\Delta \bar{w}_k\|_2 \le C$.
5. The client perturbs the clipped vector with calibrated Gaussian noise $\mathcal{N}(0, \sigma^2 \mathbf{I})$.
6. The client sends the perturbed update $\Delta \tilde{w}_k$ to the coordinator over a secure channel.
7. The coordinator combines client updates using sample-weighted averaging:

$$
w_{t+1} = w_t + \sum_{k=1}^K \frac{n_k}{N} \Delta \tilde{w}_k
$$

For protocol failure recovery and client selection policies, review [Module 05: Federated Learning Protocol](docs/05_federated_learning_protocol.md).

---

## Client-Side Differential Privacy Engine

Exchanging unperturbed model updates allows adversaries to infer sensitive training details using reconstruction attacks. PF-DAPTIV runs an $(\epsilon, \delta)$-Differential Privacy mechanism locally on each client:

![Differential Privacy Mechanism](assets/dp_mechanism.png)

The mechanism uses two steps:

First, gradient clipping caps the sensitivity of the update. If a client update exceeds clipping threshold $C = 1.0$, its magnitude is scaled down:

$$
\Delta \bar{w}_k = \Delta w_k \cdot \min\left(1, \frac{C}{\|\Delta w_k\|_2}\right)
$$

Second, calibrated zero-mean Gaussian noise is added to the clipped vector:

$$
\sigma = \frac{C \sqrt{2 \ln(1.25 / \delta)}}{\epsilon}
$$

Under baseline settings ($\epsilon = 1.0$, $\delta = 10^{-5}$, $C = 1.0$), the noise scale is $\sigma \approx 4.8447$. This step prevents adversaries from determining whether any specific network record was included in the client dataset.

Theoretical proofs and noise calibration steps are detailed in [Module 06: Differential Privacy Mathematics](docs/06_differential_privacy_mathematics.md) and [Privacy Math Reference](docs/privacy_math.md).

---

## Privacy Budget Tracking and Moments Accountant

Running consecutive federated rounds increases cumulative privacy expenditure. PF-DAPTIV tracks total privacy consumption using the Moments Accountant:

![Differential Privacy Budget & Moments Accountant](assets/differential_privacy_budget.png)

Standard composition rules sum privacy budgets linearly across rounds, creating loose bounds of $\epsilon_{\text{total}} = T \cdot \epsilon_{\text{round}}$. The Moments Accountant tracks the log moments of the privacy loss random variable, bounding total loss to $\mathcal{O}(q \epsilon \sqrt{T \ln(1/\delta)})$. This formulation permits more training iterations within a given privacy budget.

Mathematical comparisons of composition methods appear in [Module 06: Differential Privacy Mathematics](docs/06_differential_privacy_mathematics.md#multi-round-privacy-budgeting-and-composition).

---

## Architectural Module Ablation Analysis

**Not independently verified.** The figures below are the project's original narrative and have not been reproduced -- no ablation run isolating each component (local-only, clip-only, full pipeline) has actually been executed against real data. The real, measured numbers that do exist (centralized vs. FedAvg vs. PF-DAPTIV, across four real datasets) are in [Benchmark Performance Evaluation](#benchmark-performance-evaluation) below, and they contradict the "1.30% utility delta" framing implied here: on real data the federated pipeline loses far more than 1.30% relative to centralized, and on two datasets it is worse than random.

- Baseline 1D-CNN (Local Only): Trains isolated client models with no parameter exchange (91.24% F1-score) -- unverified.
- Centralized 1D-CNN: Gathers all raw telemetry onto one central server without privacy (97.45% F1-score) -- unverified.
- FedAvg (No Privacy): Standard federated training without gradient clipping or noise (96.88% F1-score) -- unverified.
- FedAvg + Clip Only: Adds $L_2$ gradient clipping without noise injection (96.42% F1-score) -- unverified.
- PF-DAPTIV (Full Pipeline): Combines FedAvg, $L_2$ norm clipping, and calibrated Gaussian noise (95.58% F1-score) -- unverified.

See [Module 08: Empirical Benchmarks and Evaluation](docs/08_empirical_benchmarks_and_evaluation.md#architectural-ablation-analysis) for the same caveat in more detail.

---

## Benchmark Performance Evaluation

**All results below are measured, not narrated** -- reproduced with [`scripts/run_real_benchmark.py`](scripts/run_real_benchmark.py) against the real, publicly downloaded datasets (not the synthetic corpus used elsewhere in this repo's test suite). Methodology: a stratified ~80,000-row sample per dataset (80/20 train/test split), 3 simulated clients, 15 federated rounds, 2 local epochs per round. A previously listed fifth dataset ("UAPD") has been removed entirely: no dataset under that name could be found published anywhere, and the repository never implemented a parser for it.

| Dataset | Setup | Binary Accuracy | Binary F1 | Multi-class Accuracy | Macro-F1 | MCC |
|---|---|:---:|:---:|:---:|:---:|:---:|
| UNSW-NB15 | Random Forest (centralized) | 94.70% | 96.13% | 89.57% | 62.41% | 0.879 |
| UNSW-NB15 | 1D-CNN (centralized, upper bound) | 89.52% | 92.47% | 80.16% | 48.19% | 0.757 |
| UNSW-NB15 | FedAvg (no DP) | 54.09% | 50.42% | 44.77% | 17.52% | 0.312 |
| UNSW-NB15 | PF-DAPTIV ($\epsilon=1.0$) | 67.66% | 80.45% | 36.86% | 9.99% | 0.076 |
| CSE-CIC-IDS2018 | Random Forest (centralized) | 96.89% | 94.87% | 96.89% | 82.98% | 0.929 |
| CSE-CIC-IDS2018 | 1D-CNN (centralized, upper bound) | 96.26% | 93.76% | 96.02% | 73.87% | 0.914 |
| CSE-CIC-IDS2018 | FedAvg (no DP) | 69.59% | 38.97% | 60.98% | 22.69% | 0.221 |
| CSE-CIC-IDS2018 | PF-DAPTIV ($\epsilon=1.0$) | 69.40% | 57.41% | 50.26% | 21.23% | 0.346 |
| Edge-IIoTset | Random Forest (centralized) | 75.03% | 64.41% | 74.73% | 57.62% | 0.501 |
| Edge-IIoTset | 1D-CNN (centralized, upper bound) | 65.99% | 40.76% | 65.70% | 33.13% | 0.328 |
| Edge-IIoTset | FedAvg (no DP) | 48.37% | 32.94% | 38.84% | 14.70% | -0.081 |
| Edge-IIoTset | PF-DAPTIV ($\epsilon=1.0$) | 50.16% | 36.60% | 38.92% | 14.76% | -0.038 |
| DAPT2020 | Random Forest (centralized) | 92.79% | 84.83% | 92.19% | 52.35% | 0.803 |
| DAPT2020 | 1D-CNN (centralized, upper bound) | 90.09% | 80.97% | 87.15% | 46.97% | 0.744 |
| DAPT2020 | FedAvg (no DP) | 74.92% | 0.00% | 74.92% | 17.13% | 0.000 |
| DAPT2020 | PF-DAPTIV ($\epsilon=1.0$) | 54.96% | 28.55% | 46.23% | 14.12% | -0.025 |

The centralized baselines are real and mostly credible (Edge-IIoTset is weaker across every model because this particular CSV mirror is missing 2 of the 9 Wireshark fields the parser reads, leaving less usable signal; DAPT2020's macro-F1 is capped by two attack stages having only 106 and 12 training examples respectively -- a genuine class-imbalance limit of the dataset, not a bug).

**The federated pipeline, however, is broken on every single dataset** -- on Edge-IIoTset and DAPT2020 it scores *below* random guessing (negative MCC), and FedAvg-no-DP collapsed to predicting one class outright on DAPT2020. Root cause, confirmed once and holding across all four datasets: `DifferentialPrivacyManager.clip_model_delta` clips the entire model's parameter update to L2-norm <= 1.0 by default, applied unconditionally regardless of whether DP is even enabled. A real local-epoch update has a natural norm around 13, so the clip discards roughly 92% of every legitimate training signal, every round, for every client -- independent of privacy noise. This is why FedAvg-no-DP performs about as badly as PF-DAPTIV throughout: the bottleneck is a miscalibrated clipping threshold, not differential privacy.

Three further data-parsing bugs surfaced and were fixed during this evaluation: `CICIDS2018_LABEL_MAP` was missing the dataset's actual (misspelled) `"Infilteration"` label; CICFlowMeter's literal `Infinity` values in rate columns were poisoning min-max scaling with NaN; and one DAPT2020 source file (`enp0s3-pvt-thursday.pcap_Flow.csv`) ships with no header row at all and is excluded rather than silently mislabeled.

Dataset characteristics and baseline model comparisons appear in [Module 08: Empirical Benchmarks and Evaluation](docs/08_empirical_benchmarks_and_evaluation.md) and [Benchmark Reference](docs/benchmarks.md).

---

## Global Federated Convergence Dynamics

**Measured**, from the actual 15-round training runs behind the [Benchmark Performance Evaluation](#benchmark-performance-evaluation) table above. Loss falls steadily but slowly for both FedAvg and PF-DAPTIV on every dataset -- consistent with the clipping bug (see above): the model is learning, just far too little per round.

| Dataset | Setup | Round 1 loss | Round 15 loss |
|---|---|:---:|:---:|
| UNSW-NB15 | FedAvg (no DP) | 1.247 | 1.047 |
| UNSW-NB15 | PF-DAPTIV | 1.252 | 1.043 |
| CSE-CIC-IDS2018 | FedAvg (no DP) | 0.591 | 0.378 |
| CSE-CIC-IDS2018 | PF-DAPTIV | 0.592 | 0.375 |
| Edge-IIoTset | FedAvg (no DP) | 1.240 | 0.997 |
| Edge-IIoTset | PF-DAPTIV | 1.238 | 1.005 |
| DAPT2020 | FedAvg (no DP) | 1.221 | 0.949 |
| DAPT2020 | PF-DAPTIV | 1.250 | 1.029 |

Loss trending down does **not** mean the model is converging to something useful -- see the actual classification metrics in the benchmark table, several of which are at or below random guessing despite this steady loss decline. Full per-round histories are saved in `results_*.json` from `scripts/run_real_benchmark.py`.

---

## Multiclass ROC Discrimination

**Not independently verified.** Per-class ROC/AUC was never computed against real data in this evaluation (the real-benchmark script reports accuracy/F1/MCC, not per-class ROC curves). Given the actual macro-F1 and MCC scores above -- several near or below zero -- the AUC values below are almost certainly not achievable and should be treated as unverified narrative pending an actual run.

- ~~Area Under the ROC Curve (AUC-ROC) metrics range from 0.978 for low-footprint Command and Control beacons to 0.992 for high-volume Reconnaissance scans. Low False Positive Rates (3.50% to 4.30%) prevent false alerts from overwhelming control room personnel.~~

---

## Stage Classification Confusion Matrix

**Measured** -- the raw confusion matrix from the centralized 1D-CNN's real CSE-CIC-IDS2018 run (rows = true stage, columns = predicted; stages with zero support in this dataset's label mapping are omitted):

| True \ Pred | Benign | S2: Init. Compromise | S3: Foothold | S4: Lateral Movement |
|---|:---:|:---:|:---:|:---:|
| Benign | 10,897 | 23 | 14 | 0 |
| S2: Initial Compromise | 1 | 2,534 | 0 | 0 |
| S3: Foothold Establishment | 4 | 0 | 1,932 | 0 |
| S4: Lateral Movement | **557** | 7 | 31 | **0** |

Benign, Initial Compromise and Foothold are all recognized well (>99%). But **Lateral Movement (mapped from the dataset's Infiltration label) is never once correctly classified** -- 557 of 595 real lateral-movement flows (94%) are predicted as Benign outright. For a system whose entire premise is detecting multi-stage APT progression, missing lateral movement essentially completely is a significant, genuine finding, not a minor caveat.

---

## Feature Explainability (SHAP and CHIFS)

**Not independently verified, and internally inconsistent with the actual code.** `SHAPExplainer` exists in `src/explainability/shap_explainer.py` and is covered by a unit test on synthetic data, but was never run against any of the four real datasets for this evaluation. Worse: the named features below (`flow_packets_per_sec`, `src_port_entropy`, `syn_flag_count`, `fwd_iat_std`, `total_bwd_bytes`, `down_up_ratio`) **do not match any of the 35 actual feature names** in `src/data/cdfv_schema.py` (the real names are `fwd_pkts_per_sec`, `syn_flag_cnt`, etc. -- there is no `src_port_entropy` or `total_bwd_bytes` field in the schema at all). This section was fabricated wholesale and should not be relied on until a real SHAP run against real CDFV output is done and reported.

---

## Privacy-Utility Pareto Frontier

**Not independently verified.** This evaluation only compared two points -- no DP ($\epsilon=0$) vs. $\epsilon=1.0$ -- not the five-point sweep implied below, and per the [Benchmark Performance Evaluation](#benchmark-performance-evaluation) table, the actual utility cost at $\epsilon=1.0$ is far larger than "1.30%" on every real dataset (in two cases the federated model is worse than random regardless of $\epsilon$). Treat the specific curve below as unreproduced narrative.

- ~~High Privacy Setting ($\epsilon = 0.5$): Provides strong confidentiality for sensitive environments, maintaining 93.8% to 94.6% detection accuracy.~~
- ~~Balanced Setting ($\epsilon = 1.0$): Recommended default, providing formal mathematical privacy with 95.14% to 96.11% accuracy.~~
- ~~Relaxed Privacy Setting ($\epsilon \ge 5.0$): Suitable when privacy rules are permissive, operating within 0.4% of non-private models.~~

---

## Quickstart Guide

### Environment Setup

Clone the repository and install required packages:

```bash
git clone https://github.com/nav6x/pf-daptiv.git
cd pf-daptiv
pip install -r requirements.txt
```

### Execution Commands

| Workflow | Objective | Command |
|---|---|---|
| Unit Test Suite | Run tests verifying schema, 1D-CNN, and federated averaging | `python -m unittest discover -s tests -p "test_*.py"` |
| Federated Training | Train federated model with differential privacy across edge clients | `python scripts/train_federated.py --rounds 15 --clients 6 --epsilon 1.0 --clip-norm 1.0` |
| Feature Attribution | Calculate SHAP feature importance scores for local models | `python scripts/explain_model.py --top-k 8` |
| Baseline Benchmarks | Run baseline models (Random Forest, MLP, SVM) for comparison | `python scripts/benchmark_baselines.py` |
| Privacy Budget Sweep | Evaluate detection accuracy across multiple epsilon values | `python scripts/sweep_privacy.py --epsilons 0.2 0.5 1.0 2.0 5.0` |

Detailed execution options and script arguments are documented in [Module 09: Operations and Deployment Guide](docs/09_operations_and_deployment_guide.md).

---

## Repository Structure

```
pf-daptiv/
|-- assets/
|   |-- ablation_study.png
|   |-- benchmark_comparison.png
|   |-- cdfv_feature_vector.png
|   |-- client_server_protocol.png
|   |-- cnn_architecture.png
|   |-- differential_privacy_budget.png
|   |-- dp_mechanism.png
|   |-- federated_convergence.png
|   |-- privacy_utility_tradeoff.png
|   |-- roc_curves.png
|   |-- shap_feature_importance.png
|   |-- stage_confusion_matrix.png
|   |-- system_pipeline.png
|   `-- threat_model_lifecycle.png
|-- config/
|   `-- default_config.yaml
|-- docs/
|   |-- README.md
|   |-- 01_foundations_and_problem_space.md
|   |-- 02_threat_model_and_apt_lifecycle.md
|   |-- 03_cdfv_telemetry_schema.md
|   |-- 04_edge_1d_cnn_architecture.md
|   |-- 05_federated_learning_protocol.md
|   |-- 06_differential_privacy_mathematics.md
|   |-- 07_explainability_and_attribution.md
|   |-- 08_empirical_benchmarks_and_evaluation.md
|   |-- 09_operations_and_deployment_guide.md
|   |-- architecture.md
|   |-- benchmarks.md
|   |-- cdfv_schema.md
|   `-- privacy_math.md
|-- scripts/
|   |-- benchmark_baselines.py
|   |-- explain_model.py
|   |-- sweep_privacy.py
|   `-- train_federated.py
|-- src/
|   |-- data/
|   |-- explainability/
|   |-- federated/
|   |-- models/
|   `-- utils/
|-- tests/
|   `-- test_pipeline.py
|-- Makefile
|-- pyproject.toml
`-- requirements.txt
```

---

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE) for terms.