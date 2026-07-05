import os
import sys
import unittest
import torch
import numpy as np
import pandas as pd

torch.set_num_threads(1)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.cdfv_schema import CDFV_FEATURE_NAMES, CDFV_CATEGORIES, APT_STAGES
from src.data.synthetic_apt import generate_synthetic_corpus, partition_data_across_clients
from src.data.dataset_loader import CDFVDataset
from src.models.cnn1d import APTClassifier1DCNN
from src.models.baselines import BaselineMLP, get_random_forest_baseline
from src.federated.privacy import DifferentialPrivacyManager
from src.federated.client import FederatedClient
from src.federated.server import FederatedServer
from src.explainability.shap_explainer import SHAPExplainer
from src.data.parsers import parse_cicids2018, parse_unsw_nb15


class TestPipeline(unittest.TestCase):
    def test_cdfv_schema(self):
        self.assertEqual(len(CDFV_FEATURE_NAMES), 35)
        self.assertEqual(len(APT_STAGES), 7)
        total_cat_features = sum(len(f) for f in CDFV_CATEGORIES.values())
        self.assertEqual(total_cat_features, 35)

    def test_synthetic_data_generation(self):
        df, y_multi, y_binary = generate_synthetic_corpus(total_samples=300, random_state=42)
        self.assertEqual(df.shape, (300, 35))
        self.assertEqual(len(y_multi), 300)
        self.assertEqual(len(y_binary), 300)
        self.assertTrue(np.all(df.values >= 0.0) and np.all(df.values <= 1.0))
        self.assertEqual(set(np.unique(y_multi)), set(range(7)))

    def test_1d_cnn_forward(self):
        model = APTClassifier1DCNN(input_dim=35, num_classes=7)
        dummy_input = torch.randn(16, 35)
        logits = model(dummy_input)
        self.assertEqual(logits.shape, (16, 7))

        probs = model.predict_proba(dummy_input)
        self.assertEqual(probs.shape, (16, 7))
        self.assertTrue(torch.allclose(torch.sum(probs, dim=-1), torch.ones(16), atol=1e-5))

        bin_probs = model.predict_binary_proba(dummy_input)
        self.assertEqual(bin_probs.shape, (16, 2))

    def test_differential_privacy_clipping(self):
        dp = DifferentialPrivacyManager(epsilon=1.0, delta=1e-5, clip_threshold=0.5)
        large_delta = {"weight": torch.ones(10, 10) * 10.0}
        clipped = dp.clip_model_delta(large_delta)
        clipped_norm = torch.norm(clipped["weight"]).item()
        self.assertLessEqual(clipped_norm, 0.5001)

    def test_federated_round(self):
        dp = DifferentialPrivacyManager(epsilon=1.0, delta=1e-5, clip_threshold=1.0)
        df, y, _ = generate_synthetic_corpus(total_samples=200, random_state=42)

        test_ds = CDFVDataset(df.values[:50], y[:50])
        partitions = partition_data_across_clients(df.values[50:], y[50:], num_clients=2)

        def model_fn():
            return APTClassifier1DCNN(input_dim=35, num_classes=7)

        clients = [
            FederatedClient(
                client_id=i,
                dataset=CDFVDataset(px, py),
                model_fn=model_fn,
                dp_manager=dp,
                local_epochs=1,
                batch_size=32,
            )
            for i, (px, py) in enumerate(partitions)
        ]

        server = FederatedServer(
            global_model=model_fn(),
            clients=clients,
            dp_manager=dp,
            test_dataset=test_ds,
        )

        loss, metrics = server.run_round(1)
        self.assertGreater(loss, 0.0)
        self.assertIn("binary_accuracy", metrics)
        self.assertIn("multi_accuracy", metrics)

    def test_shap_explainer(self):
        model = APTClassifier1DCNN(input_dim=35, num_classes=7)
        df, _, _ = generate_synthetic_corpus(total_samples=100, random_state=42)
        explainer = SHAPExplainer(model=model, background_data=df.values[:50])
        imp = explainer.compute_feature_importance(df.values[50:], num_samples=10)
        self.assertEqual(len(imp), 35)
        chifs = explainer.extract_chifs(imp, top_k=5)
        self.assertEqual(len(chifs), 5)

    def test_baseline_models(self):
        mlp = BaselineMLP(input_dim=35, num_classes=7)
        out = mlp(torch.randn(10, 35))
        self.assertEqual(out.shape, (10, 7))

        rf = get_random_forest_baseline(n_estimators=10)
        x = np.random.rand(30, 35)
        y = np.random.randint(0, 7, size=30)
        rf.fit(x, y)
        preds = rf.predict(x[:5])
        self.assertEqual(len(preds), 5)

    def test_dataset_parsers(self):
        mock_cic = pd.DataFrame({
            "Flow Duration": [1000, 2000],
            "Flow Packets/s": [10, 20],
            "Bwd Packets/s": [5, 10],
            "Flow IAT Mean": [100, 200],
            "Flow IAT Std": [10, 20],
            "Packet Length Mean": [500, 600],
            "Packet Length Variance": [50, 60],
            "SYN Flag Count": [1, 0],
            "RST Flag Count": [0, 1],
            "Dst Port": [80, 443],
            "Down/Up Ratio": [1, 2],
            "Flow IAT Min": [5, 10],
            "Label": ["Benign", "FTP-BruteForce"],
        })
        x_cic, y_cic = parse_cicids2018(mock_cic)
        self.assertEqual(x_cic.shape, (2, 35))
        self.assertEqual(list(y_cic), [0, 2])

        mock_unsw = pd.DataFrame({
            "dur": [0.5, 1.2],
            "spkts": [10, 20],
            "dpkts": [8, 15],
            "ct_dst_src_ltm": [2, 5],
            "ct_srv_src": [1, 4],
            "ct_dst_ltm": [3, 6],
            "ct_src_ltm": [2, 3],
            "sbytes": [1000, 2000],
            "dbytes": [800, 1500],
            "rate": [50, 100],
            "sjit": [10, 20],
            "attack_cat": ["Normal", "Reconnaissance"],
        })
        x_unsw, y_unsw = parse_unsw_nb15(mock_unsw)
        self.assertEqual(x_unsw.shape, (2, 35))
        self.assertEqual(list(y_unsw), [0, 1])


if __name__ == "__main__":
    unittest.main()
