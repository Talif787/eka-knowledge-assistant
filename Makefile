.PHONY: install lint type test test-unit eval migrate run worker up down

install:
	pip install -e ".[dev]"

lint:
	ruff check src tests scripts
	ruff format --check src tests scripts

type:
	mypy src

test-unit:
	pytest tests/unit

test:
	pytest

eval:
	python scripts/run_eval.py

migrate:
	alembic upgrade head

run:
	uvicorn eka.main:app --reload

worker:
	python -m eka.worker

up:
	docker compose up --build

down:
	docker compose down -v
