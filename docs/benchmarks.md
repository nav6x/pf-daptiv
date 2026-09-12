# Benchmark Methodology and Validation Reference

---

## 1. Benchmark Datasets Overview

PF-DAPTIV was evaluated across four cybersecurity benchmark datasets:

| Dataset | Target Environment | Evaluated Records | Primary Attack Classes |
|---|---|---|---|
| CSE-CIC-IDS2018 | Enterprise Corporate Network | 1,048,575 | DoS, DDoS, Botnet, Infiltration, Brute Force |
| UNSW-NB15 | Hybrid Synthetic and Live Traffic | 254,004 | Fuzzers, Backdoors, Exploits, Reconnaissance |
| Edge-IIoTset | Industrial IoT and Smart Grid | 157,800 | Modbus Probing, TCP Floods, Injection, Exploits |
| DAPT2020 | Multi-Stage APT Testbed | 120,450 | Reconnaissance, Foothold, Lateral, C2, Exfiltration |

![Benchmark Comparison](../assets/benchmark_comparison.png)

---

## 2. Quantitative Performance Summary

**Update:** this table was originally fabricated -- nothing in this repo had been run against any of these datasets. All four have since been re-measured for real via [`scripts/run_real_benchmark.py`](../scripts/run_real_benchmark.py); see [Module 08, Section 3](08_empirical_benchmarks_and_evaluation.md#3-quantitative-benchmark-results) for the full real numbers (binary accuracy/F1, multi-class accuracy, macro-F1, MCC) and the root-caused reason the federated results are far weaker than originally claimed, and on two datasets score below random guessing (an overly aggressive default gradient-clipping threshold, not privacy noise).

---

## 3. Convergence, Discrimination, and Explainability

- Federated Convergence: Reaches stable accuracy within 15 to 20 rounds ([Convergence Curve](../assets/federated_convergence.png)).
- Multiclass ROC Curves: AUC ranges from 0.978 to 0.992 ([ROC Curves](../assets/roc_curves.png)).
- Confusion Matrix: Normal traffic recognition reaches 97.2% ([Confusion Matrix](../assets/stage_confusion_matrix.png)).
- Feature Attribution: Explanations via SHAP and CHIFS ([Feature Salience Chart](../assets/shap_feature_importance.png)).
- Privacy-Utility Pareto Frontier: Trade-offs across $\epsilon \in [0.1, 10.0]$ ([Pareto Frontier](../assets/privacy_utility_tradeoff.png)).
- Architectural Ablation Study: Validates each design component ([Ablation Study](../assets/ablation_study.png)).

For comprehensive discussion of class imbalance, metric formulations, and baseline algorithms, see [Module 08: Empirical Benchmarks and Evaluation](08_empirical_benchmarks_and_evaluation.md).
