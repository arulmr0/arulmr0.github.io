.PHONY: install dev seed test lint format check docker

install:        ## Install runtime + dev dependencies
	pip install -e ".[dev]"

dev:            ## Run the API with auto-reload on http://localhost:8000
	uvicorn app.main:app --reload

seed:           ## Load demo data into the configured database
	python -m app.seed

test:           ## Run the test suite
	pytest

lint:           ## Static analysis
	ruff check . && ruff format --check .

format:         ## Auto-format
	ruff format . && ruff check . --fix

check: lint test ## Everything CI runs

docker:         ## Build and run with docker compose
	docker compose up --build
