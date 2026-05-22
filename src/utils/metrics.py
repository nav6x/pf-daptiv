from typing import Dict, List, Any
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    matthews_corrcoef,
    confusion_matrix,
)

from ..data.cdfv_schema import APT_STAGES


def evaluate_predictions(
    targets: List[int], preds: List[int], probs: List[List[float]]
) -> Dict[str, Any]:
    targets = np.array(targets)
    preds = np.array(preds)
    probs = np.array(probs)

    acc_multi = accuracy_score(targets, preds)
    f1_macro = f1_score(targets, preds, average="macro", zero_division=0)

    bin_targets = (targets > 0).astype(int)
    bin_preds = (preds > 0).astype(int)

    bin_acc = accuracy_score(bin_targets, bin_preds)
    bin_prec = precision_score(bin_targets, bin_preds, zero_division=0)
    bin_rec = recall_score(bin_targets, bin_preds, zero_division=0)
    bin_f1 = f1_score(bin_targets, bin_preds, zero_division=0)
    bin_mcc = matthews_corrcoef(bin_targets, bin_preds)

    stage_recalls = {}
    for stage_idx, stage_name in APT_STAGES.items():
        mask = targets == stage_idx
        stage_recalls[stage_name] = (
            float(np.mean(preds[mask] == stage_idx)) if np.any(mask) else 0.0
        )

    conf_mat = confusion_matrix(targets, preds, labels=list(range(7)))

    return {
        "multi_accuracy": float(acc_multi),
        "f1_macro": float(f1_macro),
        "binary_accuracy": float(bin_acc),
        "binary_precision": float(bin_prec),
        "binary_recall": float(bin_rec),
        "binary_f1": float(bin_f1),
        "binary_mcc": float(bin_mcc),
        "stage_recalls": stage_recalls,
        "confusion_matrix": conf_mat.tolist(),
    }
