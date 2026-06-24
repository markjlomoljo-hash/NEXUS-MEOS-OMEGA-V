.PHONY: install lint test benchmark

install:
	sudo pip3 install -r requirements.txt

lint:
	flake8 src/ tests/
	mypy --strict src/

test:
	pytest tests/test_integration_full.py --cov=src --cov-report=term-missing

benchmark:
	python3 tests/benchmark_suite.py
