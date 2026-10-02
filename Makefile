install:
	pip install -r requirements.txt
lint:
	python -m compileall -q bot

test:
	pytest -q

migrate:
	alembic upgrade head

up:
	docker compose up -d

release:
	python scripts/build_release.py

chaos:
	pytest -q tests/test_extreme_chaos.py
