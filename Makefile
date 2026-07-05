.PHONY: test train benchmark sweep explain clean

test:
	python -m unittest discover -s tests -p "test_*.py"

train:
	python scripts/train_federated.py --rounds 15 --clients 6

benchmark:
	python scripts/benchmark_baselines.py

sweep:
	python scripts/sweep_privacy.py

explain:
	python scripts/explain_model.py --top-k 8

clean:
	rm -rf __pycache__ src/**/__pycache__ scripts/__pycache__ tests/__pycache__ .pytest_cache
