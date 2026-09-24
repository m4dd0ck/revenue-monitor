.PHONY: build generate load dbt metrics all test test-all lint clean \
	dashboard-sources dashboard-dev dashboard-build

build:
	uv sync
	cd dashboard && npm ci

generate:
	uv run revmon generate

load:
	uv run revmon load

dbt:
	uv run dbt build --profiles-dir .

metrics:
	uv run revmon metrics

# full pipeline from nothing: synthetic data → warehouse → dashboard data
all: generate load dbt dashboard-sources

test:
	uv run pytest

test-all:
	uv run pytest -m "integration or not integration"

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/

dashboard-sources:
	cd dashboard && npm run sources

dashboard-dev:
	cd dashboard && npm run dev

dashboard-build:
	cd dashboard && npm run build:strict

clean:
	rm -rf data/ target/ logs/ dashboard/build/ dashboard/.evidence/template
