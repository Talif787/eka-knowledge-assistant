.PHONY: install lint type test test-unit migrate run up down

install:
	pip install -e ".[dev]"

lint:
	ruff check src tests
	ruff format --check src tests

type:
	mypy src

test-unit:
	pytest tests/unit

test:
	pytest

migrate:
	alembic upgrade head

run:
	uvicorn eka.main:app --reload

up:
	docker compose up --build

down:
	docker compose down -v
