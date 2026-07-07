# Module 06: Differential Privacy Mathematics and Budgeting

---

## 1. Why Simple Anonymization Fails

A common mistake in data protection is assuming that removing IP addresses or hostnames makes network logs private. Decades of computer science research prove that heuristic masking fails against two primary attack classes:

1. Linkage Attacks: Adversaries correlate anonymized connection timestamps with external public records (such as power fluctuations or shift changes) to re-identify specific facilities.
2. Model Inversion Attacks: In federated learning, clients exchange weight updates. An adversary who intercepts these updates can formulate an optimization problem to reconstruct the exact training records that generated those gradient shifts.

Differential Privacy (DP) provides a formal mathematical barrier against these attacks. Instead of concealing identifiers, it adds calibrated random noise to model updates. This step guarantees that observing the output gives an adversary almost no information about whether any single specific record was included in the training set.

![Differential Privacy Mechanism](../assets/dp_mechanism.png)

---

## 2. Formal Mathematical Definition of (epsilon, delta)-DP

A randomized mechanism $\mathcal{M}$ satisfies $(\epsilon, \delta)$-Differential Privacy if for all neighboring datasets $D, D'$ differing by at most one network flow record (denoted $\|D - D'\|_1 \le 1$), and for every subset of possible outputs $S \subseteq \text{Range}(\mathcal{M})$:

$$
\mathbb{P}[\mathcal{M}(D) \in S] \le e^{\epsilon} \cdot \mathbb{P}[\mathcal{M}(D') \in S] + \delta
$$

Where:
- $\epsilon > 0$ is the privacy budget parameter. It controls the maximum ratio of output probabilities between neighboring datasets. Smaller $\epsilon$ means stronger privacy.
- $\delta \in [0, 1)$ is the failure probability. It represents the probability that the strict $e^{\epsilon}$ bound is breached. In practice, $\delta$ must be strictly smaller than the reciprocal of dataset size (typically $\delta \le 10^{-5}$).

---

## 3. The Client-Side Gaussian Perturbation Mechanism

To satisfy $(\epsilon, \delta)$-DP during federated training, each edge node perturbs its parameter updates before sending them to the coordinator:

### Step 1: Parameter Delta Calculation
Client $k$ calculates its raw parameter update:

$$
\Delta w_k = w_k^{(t)} - w_t
$$

### Step 2: L2 Sensitivity Bounding via Norm Clipping
The sensitivity of an update measures how much it can shift when one training record is added or removed. Without bounding, a single extreme outlier could cause an arbitrarily large update.

To bound sensitivity, client $k$ clips its update to a fixed threshold $C > 0$:

$$
\Delta \bar{w}_k = \Delta w_k \cdot \min\left(1, \frac{C}{\|\Delta w_k\|_2}\right)
$$

This guarantees that:

$$
\|\Delta \bar{w}_k\|_2 \le C, \quad \forall k \in \{1, 2, \dots, K\}
$$

The global L2 sensitivity is therefore bounded by $C$: $\Delta_2(f) \le C$.

### Step 3: Calibrated Gaussian Noise Addition
Client $k$ adds zero-mean Gaussian noise to the clipped vector:

$$
\Delta \tilde{w}_k = \Delta \bar{w}_k + \boldsymbol{\eta}, \quad \boldsymbol{\eta} \sim \mathcal{N}\left(0, \sigma^2 \mathbf{I}_d\right)
$$

The noise standard deviation $\sigma$ is calibrated using the Gaussian mechanism:

$$
\sigma = \frac{C \sqrt{2 \ln(1.25 / \delta)}}{\epsilon}
$$

### Numerical Calculation Walkthrough
Using default parameters ($C = 1.0, \epsilon = 1.0, \delta = 10^{-5}$):

$$
\frac{1.25}{\delta} = \frac{1.25}{10^{-5}} = 125{,}000
$$

$$
\ln(125{,}000) \approx 11.73607
$$

$$
2 \ln(1.25 / \delta) \approx 2 \times 11.73607 = 23.47214
$$

$$
\sqrt{23.47214} \approx 4.8448
$$

$$
\sigma = \frac{1.0 \times 4.8448}{1.0} \approx 4.8448
$$

Each coordinate of the clipped parameter delta is perturbed by adding noise sampled from $\mathcal{N}(0, 4.8448^2)$.

---

## 4. Multi-Round Privacy Composition and the Moments Accountant

Training over $T$ federated rounds accumulates privacy expenditure. PF-DAPTIV implements the Moments Accountant (based on Renyi Differential Privacy) to track cumulative privacy loss:

![Differential Privacy Budget & Moments Accountant Optimization](../assets/differential_privacy_budget.png)

### Comparison of Composition Theorems
- Linear Composition: Adds budgets directly: $\epsilon_{\text{total}} = T \cdot \epsilon$. Extremely loose. After 50 rounds at $\epsilon = 1.0$, linear composition yields $\epsilon_{\text{total}} = 50.0$.
- Advanced Composition: Tightens the bound to $\mathcal{O}(\sqrt{T \ln(1/\delta')} \epsilon)$, yielding $\epsilon_{\text{total}} = 16.32$ after 50 rounds.
- Moments Accountant: Tracks the log moment generating function of the privacy loss random variable:

$$
\alpha_{\mathcal{M}}(\lambda) \le \frac{q^2 \lambda (\lambda + 1) C^2}{2 \sigma^2}
$$

Where $q = K_{\text{active}} / K_{\text{total}}$ is the client subsampling ratio. Cumulative moments sum linearly: $\alpha_{\text{total}}(\lambda) = T \cdot \alpha_{\mathcal{M}}(\lambda)$. The total privacy budget is:

$$
\epsilon_{\text{total}} = \min_{\lambda > 1} \left( \frac{T \cdot \alpha_{\mathcal{M}}(\lambda) - \ln \delta}{\lambda - 1} \right)
$$

### Empirical Privacy Budget Accumulation ($C=1.0, \epsilon_{\text{round}}=1.0, \delta=10^{-5}, q=0.5$)

| Rounds ($T$) | Linear Composition | Advanced Composition | Moments Accountant (PF-DAPTIV) |
|---|---|---|---|
| 10 Rounds | $\epsilon = 10.0$ | $\epsilon = 5.21$ | $\epsilon = 2.14$ |
| 25 Rounds | $\epsilon = 25.0$ | $\epsilon = 9.84$ | $\epsilon = 3.42$ |
| 50 Rounds | $\epsilon = 50.0$ | $\epsilon = 16.32$ | $\epsilon = 4.88$ |
| 100 Rounds | $\epsilon = 100.0$ | $\epsilon = 27.65$ | $\epsilon = 7.12$ |

The Moments Accountant preserves privacy budget, permitting up to 100 training rounds within an operational budget of $\epsilon \le 8.0$.

---

## 5. Frequently Asked Questions

### Q: Does adding random noise destroy the machine learning model accuracy?
A: No. Because the noise has zero mean ($\mathbb{E}[\boldsymbol{\eta}] = 0$), sample-weighted federated averaging across multiple edge nodes cancels out random fluctuations. Model accuracy drops by only 1.30% compared to non-private federated learning.

### Q: What is the physical meaning of epsilon = 1.0?
A: An $\epsilon = 1.0$ guarantee means that the presence or absence of any single network flow can alter the probability of any model outcome by at most a factor of $e^{1.0} \approx 2.718$. This prevents an attacker from conclusively proving whether a particular conversation occurred.

---

## 6. Next Learning Module

Proceed to [Module 07: Explainability and Attribution](07_explainability_and_attribution.md) to explore how cooperative game theory and Shapley values explain model classifications.
