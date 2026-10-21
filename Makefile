.PHONY: build generate load dbt metrics all test test-all lint clean \
	dashboard-sources dashboard-dev dashboard-build

build: ## Install the Python and Node dependencies
	uv sync
	cd dashboard && npm ci

generate: ## Generate the synthetic Stripe-shaped data
	uv run revmon generate

load: ## Load the generated data into DuckDB
	uv run revmon load

dbt: ## Build the dbt models
	uv run dbt build --profiles-dir .

metrics: ## Print the MetricForge metrics table
	uv run revmon metrics

all: generate load dbt dashboard-sources ## The four pipeline steps in order, from nothing to dashboard data

test: ## Unit tests
	uv run pytest

test-all: ## Unit tests plus the end-to-end pipeline test
	uv run pytest -m "integration or not integration"

lint: ## ruff and mypy
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/

dashboard-sources: ## Export the marts for Evidence
	cd dashboard && npm run sources

dashboard-dev: ## Serve Evidence locally
	cd dashboard && npm run dev

dashboard-build: ## Build the dashboard strictly, as CI does
	cd dashboard && npm run build:strict

clean: ## Delete the generated data, warehouse, dbt artifacts and dashboard build
	rm -rf data/ target/ logs/ dashboard/build/ dashboard/.evidence/template
