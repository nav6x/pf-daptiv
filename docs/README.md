# PF-DAPTIV Documentation

This directory contains technical specifications, mathematical derivations, and operational documentation for the PF-DAPTIV framework.

---

## Documentation Modules

| Module | Document | Description |
|---|---|---|
| Module 01 | [Foundations and Problem Space](01_foundations_and_problem_space.md) | Industrial IoT architecture, APT characteristics, and non-IID data distribution |
| Module 02 | [Threat Model and APT Lifecycle](02_threat_model_and_apt_lifecycle.md) | Multi-stage kill chain, 6 discrete attack stages, and MITRE ATT&CK mapping |
| Module 03 | [CDFV Telemetry Schema](03_cdfv_telemetry_schema.md) | 35-position feature vector, functional domains, and min-max normalization |
| Module 04 | [Edge 1D-CNN Architecture](04_edge_1d_cnn_architecture.md) | Layer parameters, receptive fields, loss formulation, and hardware constraints |
| Module 05 | [Federated Learning Protocol](05_federated_learning_protocol.md) | FedAvg aggregation, client synchronization loop, and fault tolerance |
| Module 06 | [Differential Privacy Mathematics](06_differential_privacy_mathematics.md) | Sensitivity bounding, Gaussian noise calibration, and Moments Accountant |
| Module 07 | [Explainability and Attribution](07_explainability_and_attribution.md) | Shapley values, local attribution, and federated CHIFS aggregation |
| Module 08 | [Empirical Benchmarks and Evaluation](08_empirical_benchmarks_and_evaluation.md) | Benchmark dataset results, ROC discrimination, and ablation studies |
| Module 09 | [Operations and Deployment Guide](09_operations_and_deployment_guide.md) | CLI workflows, configuration parameters, and production deployment |

---

## Technical Specifications

- [System Architecture](architecture.md): Protocol state transitions, node coordination, and message structures.
- [CDFV Schema Specification](cdfv_schema.md): Complete feature index and normalization bounds.
- [Privacy Math Reference](privacy_math.md): Differential privacy proofs and numerical derivations.
- [Benchmark Methodology Reference](benchmarks.md): Dataset profiles, evaluation metrics, and comparative baselines.
