# Module 09: Operations and Deployment Guide

---

## 1. System Requirements and Environment Setup

PF-DAPTIV runs on standard Linux, macOS, and Windows workstations as well as embedded industrial edge computers (such as Raspberry Pi 4, NVIDIA Jetson, and Siemens IPCs).

### Prerequisites
- Python 3.10 or higher
- PyTorch 2.0 or higher
- 4 GB RAM minimum (8 GB recommended for multi-client simulations)
- 1 GB free disk storage

### Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/nav6x/pf-daptiv.git
cd pf-daptiv
pip install -r requirements.txt
```

---

## 2. Command-Line Interface (CLI) Workflows

The `scripts/` directory contains automated workflows for training, evaluation, privacy analysis, and explainability:

### Workflow 1: Running the Automated Unit Test Suite
Verifies feature schemas, 1D-CNN layer dimensions, gradient clipping, Gaussian noise generation, and FedAvg aggregation:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

### Workflow 2: Federated Training Simulation
Simulates a multi-client federated training process with client-side differential privacy:

```bash
python scripts/train_federated.py \
    --rounds 15 \
    --clients 6 \
    --local-epochs 2 \
    --batch-size 32 \
    --lr 0.001 \
    --epsilon 1.0 \
    --delta 1e-5 \
    --clip-norm 1.0
```

Key Arguments:
- `--rounds`: Number of federated communication cycles (default: 15).
- `--clients`: Number of distributed edge clients participating (default: 6).
- `--local-epochs`: Training iterations executed locally per client per round (default: 2).
- `--epsilon`: Target privacy budget $\epsilon$ per round (default: 1.0).
- `--clip-norm`: Maximum L2 norm threshold $C$ for parameter delta clipping (default: 1.0).

### Workflow 3: Baseline Comparative Benchmarking
Runs comparative benchmarks against centralized Random Forest, Support Vector Machines (SVM), Multi-Layer Perceptrons (MLP), and centralized 1D-CNN:

```bash
python scripts/benchmark_baselines.py
```

### Workflow 4: Privacy Budget Sweep
Sweeps detection performance across different values of $\epsilon$ to construct the privacy-utility Pareto frontier:

```bash
python scripts/sweep_privacy.py --epsilons 0.2 0.5 1.0 2.0 5.0
```

### Workflow 5: Model Explainability and SHAP Attribution
Generates local Shapley value rankings and global CHIFS feature attribution profiles:

```bash
python scripts/explain_model.py --top-k 8
```

---

## 3. Configuration Management

System hyperparameter defaults are configured in `config/default_config.yaml`. **This section previously quoted a version of the file that did not match reality** (wrong filter counts, wrong round/epoch/batch-size defaults, and missing fields) -- below is the actual current content:

```yaml
federated:
  num_clients: 6
  rounds: 20
  local_epochs: 5
  batch_size: 64
  learning_rate: 0.001
  weight_decay: 0.0001
  aggregation: "FedAvg"

model:
  architecture: "1D-CNN"
  input_dim: 35
  conv1_filters: 64
  conv1_kernel: 3
  conv2_filters: 128
  conv2_kernel: 3
  pool_size: 2
  dense_units: 64
  dropout_rate: 0.4
  num_classes: 7

privacy:
  enabled: true
  epsilon: 1.0
  delta: 1.0e-5
  clip_threshold: 1.0
  dual_layer_noise: true

data:
  cdfv_features: 35
  smote_ratio: 0.33
  test_split: 0.2
  val_split: 0.1
  random_seed: 42

explainability:
  num_background_samples: 100
  num_explain_samples: 50
  chifs_top_k: 8
```

Note the config file's own defaults (20 rounds, 5 local epochs, 6 clients) differ from the `--rounds 15 --clients 6 --local-epochs 2` example invocation in Workflow 2 above and from this evaluation's real benchmark methodology (15 rounds, 3 clients, 2 local epochs) -- none of these are wrong, they're just three different, inconsistently-documented defaults. Treat command-line flags as authoritative over either documented default.

---

## 4. Industrial Deployment Considerations

When moving from local simulation to field deployment across physical industrial facilities:

1. Communication Security: All communication between edge nodes and the central coordinator must use mutual TLS (mTLS) with client-side X.509 certificates.
2. Network Latency: With the model's real ~91,399 parameters at float32, each parameter update is ~357 KB (see [Module 04](04_edge_1d_cnn_architecture.md#3-parameter-count-and-memory-footprint)) -- still small enough that communication completes within seconds over standard industrial cellular (4G/5G) or plant Ethernet links, but the previous "under 300 kilobytes" figure was based on the wrong (smaller) architecture and is now corrected.
3. Edge Storage: Edge nodes retain only recent telemetry windows. Normalized CDFV vectors occupy less than 200 bytes per flow record, permitting months of local history on modest SSD storage.

---

## 5. Troubleshooting Common Issues

### Issue 1: Out of Memory During Local Simulation
- Cause: Simulating too many clients simultaneously in a single process.
- Solution: Reduce `--clients` to 4 or decrease `--batch-size` to 16.

### Issue 2: Slow Convergence Under Strict Privacy (epsilon < 0.5)
- Cause: High Gaussian noise scale ($\sigma > 9.69$) slows gradient updates.
- Solution: Increase the number of local epochs to `--local-epochs 3` or increase `--rounds` to 25 to allow the global model to average out perturbation noise.

---

## 6. End of Curriculum

You have completed the PF-DAPTIV knowledge base curriculum. For technical specifications, return to the [Curriculum Map](README.md) or review specific modules.
