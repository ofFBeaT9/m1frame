.PHONY: help install dev qa lint typecheck clean build run

help:
	@echo "m1frame — available commands:"
	@echo "  make install     Install production dependencies"
	@echo "  make dev         Install all dev + prod dependencies"
	@echo "  make qa          Run full QA suite (no API key needed)"
	@echo "  make lint        Run ruff linter"
	@echo "  make typecheck   Run mypy type checker"
	@echo "  make clean       Remove build artifacts and caches"
	@echo "  make build       Build distributable package"
	@echo "  make run GOAL=.. Run m1frame workflow"

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements.txt
	pip install ruff mypy pytest

qa:
	python scripts/qa_validate.py

lint:
	ruff check .

typecheck:
	mypy agents/ llm_client.py --ignore-missing-imports

clean:
	rm -rf dist/ build/ *.egg-info __pycache__ agents/__pycache__ scripts/__pycache__
	find . -name "*.pyc" -delete
	find . -name ".DS_Store" -delete

build: clean
	pip install build
	python -m build

run:
	python scripts/run_workflow.py --goal "$(GOAL)"
