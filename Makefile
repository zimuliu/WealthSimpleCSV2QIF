.PHONY: help install install-dev test test-verbose coverage coverage-html coverage-report clean lint format check-format type-check all-checks

# Default target
help:
	@echo "Available commands:"
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo "  test           Run tests"
	@echo "  test-verbose   Run tests with verbose output"
	@echo "  coverage       Run tests with coverage"
	@echo "  coverage-html  Generate HTML coverage report"
	@echo "  coverage-report View coverage report in browser"
	@echo "  lint           Run linting checks"
	@echo "  format         Format code with black and isort"
	@echo "  check-format   Check code formatting"
	@echo "  type-check     Run type checking with mypy"
	@echo "  all-checks     Run all quality checks"
	@echo "  clean          Clean up generated files"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

# Testing
test:
	python -m pytest

test-verbose:
	python -m pytest -v

coverage:
	python -m pytest --cov=app --cov-report=term-missing

coverage-html:
	python -m pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo "HTML coverage report generated in htmlcov/index.html"

coverage-report: coverage-html
	@if command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open htmlcov/index.html; \
	else \
		echo "Please open htmlcov/index.html in your browser"; \
	fi

# Code quality
lint:
	python -m flake8 app tests

format:
	python -m black app tests
	python -m isort app tests

check-format:
	python -m black --check app tests
	python -m isort --check-only app tests

type-check:
	@if command -v mypy >/dev/null 2>&1; then \
		python -m mypy app; \
	else \
		echo "mypy not installed, skipping type check"; \
	fi

all-checks: lint check-format type-check test

# Cleanup
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf */*/__pycache__/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
