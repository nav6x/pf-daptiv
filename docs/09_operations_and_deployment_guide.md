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

System hyperparameter defaults are configured in `config/default_config.yaml`:

```yaml
federated:
  rounds: 15
  num_clients: 6
  fraction_fit: 1.0
  local_epochs: 2
  batch_size: 32
  learning_rate: 0.001

privacy:
  epsilon: 1.0
  delta: 0.00001
  clip_norm: 1.0

model:
  input_dim: 35
  num_classes: 6
  conv1_filters: 32
  conv2_filters: 64
  dense_units: 128
  dropout_rate: 0.3
```

---

## 4. Industrial Deployment Considerations

When moving from local simulation to field deployment across physical industrial facilities:

1. Communication Security: All communication between edge nodes and the central coordinator must use mutual TLS (mTLS) with client-side X.509 certificates.
2. Network Latency: Because parameter updates are under 300 kilobytes, communication completes within seconds over standard industrial cellular (4G/5G) or plant Ethernet links.
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
