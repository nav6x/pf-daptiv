# Module 08: Empirical Benchmarks and Performance Evaluation

---

## 1. The Four Evaluated Benchmark Datasets

To ensure rigorous validation across diverse operating conditions, PF-DAPTIV was evaluated on four cybersecurity benchmark datasets:

| Dataset | Target Environment | Primary Traffic Profiles | Records Evaluated |
|---|---|---|---|
| CSE-CIC-IDS2018 | Enterprise Corporate Network | DoS, DDoS, Botnets, Infiltration, Web Attacks, Brute Force | 1,048,575 |
| UNSW-NB15 | Hybrid Synthetic & Live Traffic | Fuzzers, Backdoors, Exploits, Reconnaissance, Shellcode, Worms | 254,004 |
| Edge-IIoTset | Industrial IoT & Smart Factory | Modbus Probing, TCP Floods, Injection, Ransomware, Exploits | 157,800 |
| DAPT2020 | Multi-Stage APT Testbed | Reconnaissance, Foothold Staging, Lateral Movement, C2, Exfiltration | 120,450 |

![Benchmark Comparison](../assets/benchmark_comparison.png)

---

## 2. The Seven Evaluation Metrics and Class Imbalance

Network intrusion datasets suffer from extreme class imbalance: benign traffic accounts for 90 to 98 percent of records. Relying exclusively on standard Accuracy is misleading. PF-DAPTIV evaluates performance across seven metrics:

1. Accuracy: Fraction of total correct predictions: $\frac{\text{TP} + \text{TN}}{\text{TP} + \text{TN} + \text{FP} + \text{FN}}$.
2. Precision: Fraction of positive alarms that were genuine attacks: $\frac{\text{TP}}{\text{TP} + \text{FP}}$.
3. Recall (Detection Rate): Fraction of actual attacks successfully detected: $\frac{\text{TP}}{\text{TP} + \text{FN}}$.
4. F1-Score: Harmonic mean of Precision and Recall: $2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$.
5. False Positive Rate (FPR): Fraction of clean traffic misclassified as attacks: $\frac{\text{FP}}{\text{FP} + \text{TN}}$.
6. Matthews Correlation Coefficient (MCC): Balanced correlation metric robust to severe class imbalance:

$$
\text{MCC} = \frac{\text{TP} \cdot \text{TN} - \text{FP} \cdot \text{FN}}{\sqrt{(\text{TP} + \text{FP})(\text{TP} + \text{FN})(\text{TN} + \text{FP})(\text{TN} + \text{FN})}}
$$

7. Area Under the ROC Curve (AUC-ROC): Aggregate measure of classification discrimination across all operating thresholds.

---

## 3. Quantitative Benchmark Results

**Update:** the table below was originally fabricated -- no code in this repository had ever been run against any of these datasets. All four have since been re-measured for real using [`scripts/run_real_benchmark.py`](../scripts/run_real_benchmark.py) (stratified ~80,000-row sample per dataset, 80/20 split, 3 simulated clients, 15 federated rounds, 2 local epochs).

| Dataset | Setup | Binary Accuracy | Binary F1 | Multi-class Accuracy | Macro-F1 | MCC |
|---|---|:---:|:---:|:---:|:---:|:---:|
| UNSW-NB15 | Random Forest (centralized) | 94.70% | 96.13% | 89.57% | 62.41% | 0.879 |
| UNSW-NB15 | 1D-CNN (centralized, upper bound) | 89.52% | 92.47% | 80.16% | 48.19% | 0.757 |
| UNSW-NB15 | FedAvg (No DP) | 54.09% | 50.42% | 44.77% | 17.52% | 0.312 |
| UNSW-NB15 | PF-DAPTIV ($\epsilon=1.0$) | 67.66% | 80.45% | 36.86% | 9.99% | 0.076 |
| CSE-CIC-IDS2018 | Random Forest (centralized) | 96.89% | 94.87% | 96.89% | 82.98% | 0.929 |
| CSE-CIC-IDS2018 | 1D-CNN (centralized, upper bound) | 96.26% | 93.76% | 96.02% | 73.87% | 0.914 |
| CSE-CIC-IDS2018 | FedAvg (No DP) | 69.59% | 38.97% | 60.98% | 22.69% | 0.221 |
| CSE-CIC-IDS2018 | PF-DAPTIV ($\epsilon=1.0$) | 69.40% | 57.41% | 50.26% | 21.23% | 0.346 |
| Edge-IIoTset | Random Forest (centralized) | 75.03% | 64.41% | 74.73% | 57.62% | 0.501 |
| Edge-IIoTset | 1D-CNN (centralized, upper bound) | 65.99% | 40.76% | 65.70% | 33.13% | 0.328 |
| Edge-IIoTset | FedAvg (No DP) | 48.37% | 32.94% | 38.84% | 14.70% | -0.081 |
| Edge-IIoTset | PF-DAPTIV ($\epsilon=1.0$) | 50.16% | 36.60% | 38.92% | 14.76% | -0.038 |
| DAPT2020 | Random Forest (centralized) | 92.79% | 84.83% | 92.19% | 52.35% | 0.803 |
| DAPT2020 | 1D-CNN (centralized, upper bound) | 90.09% | 80.97% | 87.15% | 46.97% | 0.744 |
| DAPT2020 | FedAvg (No DP) | 74.92% | 0.00% | 74.92% | 17.13% | 0.000 |
| DAPT2020 | PF-DAPTIV ($\epsilon=1.0$) | 54.96% | 28.55% | 46.23% | 14.12% | -0.025 |

The real results show the federated pipeline performing far below the centralized baselines and far below what was originally (falsely) claimed -- on Edge-IIoTset and DAPT2020 it scores *below random guessing* (negative MCC), and FedAvg-no-DP collapsed outright to a single-class predictor on DAPT2020. Root cause, confirmed consistently across all four datasets: `DifferentialPrivacyManager.clip_model_delta` clips the entire model's parameter update to L2-norm <= 1.0 by default, applied unconditionally regardless of whether DP is enabled. A real local-epoch update has a natural norm around 13, so the clip destroys roughly 92% of the legitimate training signal every round -- independent of privacy noise. This is why FedAvg-no-DP and PF-DAPTIV score similarly poorly throughout.

Three further data-parsing bugs surfaced and were fixed during this evaluation: `CICIDS2018_LABEL_MAP` was missing the dataset's actual (misspelled) `"Infilteration"` label; CICFlowMeter's literal `Infinity` values in rate columns were poisoning min-max scaling with NaN; and one DAPT2020 source file (`enp0s3-pvt-thursday.pcap_Flow.csv`) ships with no header row at all and is excluded rather than silently mislabeled. Edge-IIoTset's weaker centralized scores reflect a genuine limitation of this CSV mirror (2 of the 9 Wireshark fields the parser reads have no equivalent column here), and DAPT2020's low macro-F1 reflects real, severe class imbalance (two attack stages have only 106 and 12 training examples) -- both are properties of the data, not bugs.

Sections 4-7 below have now been reconciled against real measurements where the data exists (4, 5, 6), and clearly marked unreproduced where it does not (part of 5, and 7).

---

## 4. Comparison Against Centralized and Local Baselines

**Replaced with measured DAPT2020 results** (the original table below claimed a "1D-CNN Local Client Only" and SVM/MLP baselines that were never run; this evaluation did not reproduce those specific configurations either, so they are omitted rather than left in place):

| Model Architecture | Training Topology | Privacy Protection | Binary F1 | Macro-F1 | MCC |
|---|---|---|:---:|:---:|:---:|
| Random Forest (100 Trees) | Centralized Pooled | None | 84.83% | 52.35% | 0.803 |
| 1D-CNN (Centralized) | Centralized Pooled | None | 80.97% | 46.97% | 0.744 |
| FedAvg | Federated Edge Nodes | None | 0.00% | 17.13% | 0.000 |
| **PF-DAPTIV (Full Pipeline)** | **Federated Edge Nodes** | **$(\epsilon=1.0, \delta=10^{-5})$-DP** | **28.55%** | **14.12%** | **-0.025** |

Centralized models substantially outperform both federated variants on real DAPT2020 data. PF-DAPTIV does not "reach 95.58% without data sharing" as the original claim stated -- its measured MCC of -0.025 means it performs indistinguishably from random guessing.

---

## 5. Convergence Trajectory and Multiclass Discrimination

**Convergence is measured**; ROC discrimination is not. Loss falls steadily across all 15 rounds for both FedAvg and PF-DAPTIV, on every dataset -- e.g. DAPT2020 FedAvg goes from 1.221 to 0.949, PF-DAPTIV from 1.250 to 1.029 (full per-round histories in `results_*.json`). This confirms the models are training, not stuck -- the clipping bug limits *how much* signal survives each round, not whether the optimizer is moving at all.

The multiclass ROC/AUC figures below were never computed against real data and are **not verified**:

- ~~Stage 1 (Reconnaissance): AUC = 0.992~~
- ~~Stage 2 (Weaponization): AUC = 0.985~~
- ~~Stage 3 (Delivery and Exploit): AUC = 0.988~~
- ~~Stage 4 (Installation): AUC = 0.981~~
- ~~Stage 5 (Command and Control): AUC = 0.978~~
- ~~Stage 6 (Actions and Exfiltration): AUC = 0.991~~

---

## 6. Confusion Matrix Analysis

**Measured** -- real confusion matrix from the centralized 1D-CNN's CSE-CIC-IDS2018 run:

| True \ Pred | Benign | S2: Init. Compromise | S3: Foothold | S4: Lateral Movement |
|---|:---:|:---:|:---:|:---:|
| Benign | 10,897 | 23 | 14 | 0 |
| S2: Initial Compromise | 1 | 2,534 | 0 | 0 |
| S3: Foothold Establishment | 4 | 0 | 1,932 | 0 |
| S4: Lateral Movement | 557 | 7 | 31 | 0 |

Benign, Initial Compromise and Foothold recognize well (>99%), but Lateral Movement (the dataset's Infiltration label) is **never once correctly classified** -- 94% of real lateral-movement flows are predicted Benign. This is a genuine, significant finding for a system whose stated purpose is multi-stage APT detection, and directly contradicts the original claim's "97.2% Normal Traffic" / "95.8% Reconnaissance" framing, which used stage names this dataset's labels don't even produce.

---

## 7. Privacy-Utility Pareto Frontier

**Not independently verified.** This evaluation compared exactly two points ($\epsilon=0$ vs. $\epsilon=1.0$), not the five-point sweep below, and the measured utility cost at $\epsilon=1.0$ (see Section 3 and Section 4) is far larger than "1.30%" on every real dataset -- in two cases the federated model scores below random regardless of $\epsilon$, meaning privacy noise isn't even the binding constraint. The table below remains unreproduced original narrative:

- ~~$\epsilon = 0.1$, $\sigma = 48.448$, Maximum Confidentiality, 89.20% F1, $-7.68\%$ delta~~
- ~~$\epsilon = 0.5$, $\sigma = 9.690$, High Confidentiality, 93.85% F1, $-3.03\%$ delta~~
- ~~$\epsilon = 1.0$, $\sigma = 4.845$, Balanced (Recommended), 95.58% F1, $-1.30\%$ delta~~
- ~~$\epsilon = 2.0$, $\sigma = 2.422$, Moderate Privacy, 96.35% F1, $-0.53\%$ delta~~
- ~~$\epsilon = 5.0$, $\sigma = 0.969$, Relaxed Privacy, 96.65% F1, $-0.23\%$ delta~~
- ~~Non-Private, $\sigma = 0.000$, No DP, 96.88% F1, $0.00\%$ delta~~

Setting $\epsilon = 1.0$ represents the optimal operational trade-off: strong mathematical confidentiality with only a 1.30% utility delta.

---

## 8. Next Learning Module

Proceed to [Module 09: Operations and Deployment Guide](09_operations_and_deployment_guide.md) for complete instructions on running simulations, benchmarking scripts, and deploying PF-DAPTIV.
