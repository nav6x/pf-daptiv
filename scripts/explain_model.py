
import os
import sys
import argparse
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.synthetic_apt import generate_synthetic_corpus
from src.data.cdfv_schema import get_category_for_feature
from src.models.cnn1d import APTClassifier1DCNN
from src.explainability.shap_explainer import SHAPExplainer




def parse_args():
    parser = argparse.ArgumentParser(description="PF-DAPTIV explainability and CHIFS extraction")
    parser.add_argument("--model-path", type=str, default="checkpoints/global_model.pt", help="Path to checkpoint")
    parser.add_argument("--top-k", type=int, default=8, help="Number of CHIFS features to select")
    parser.add_argument("--num-samples", type=int, default=100, help="Evaluation sample count")
    return parser.parse_args()


def main():
    args = parse_args()

    model = APTClassifier1DCNN(input_dim=35, num_classes=7)
    if os.path.exists(args.model_path):
        print("[+] loading model weights from", args.model_path)
        model.load_state_dict(torch.load(args.model_path, map_location="cpu"))
    else:
        print("[-] checkpoint %s not found; running on randomly initialized weights" % args.model_path)

    df, _, _ = generate_synthetic_corpus(total_samples=1000, random_state=42)
    x = df.values
    background = x[:200]
    eval_set = x[200 : 200 + args.num_samples]

    print("[*] computing Shapley attribution across %d samples..." % len(eval_set))
    explainer = SHAPExplainer(model=model, background_data=background)
    importance = explainer.compute_feature_importance(eval_set, num_samples=args.num_samples)
    chifs = explainer.extract_chifs(importance, top_k=args.top_k)

    print("\nCondensed High-Impact Feature Subsets (CHIFS):")
    print(f"{'Rank':<6}{'Feature Name':<28}{'Category':<30}{'Importance':<12}")
    print("-" * 76)
    for rank, (feat, imp) in enumerate(chifs, start=1):
        cat = get_category_for_feature(feat)
        print(f"{rank:<6}{feat:<28}{cat:<30}{imp * 100:.2f}%")
    print("-" * 76)

    total_coverage = sum(v for _, v in chifs)
    print(f"Total coverage of top-{args.top_k} features: {total_coverage * 100:.2f}%\n")


if __name__ == "__main__":
    main()
