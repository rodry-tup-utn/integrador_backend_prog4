PROJECT_NAME=integrador

init:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt
	docker compose -p $(PROJECT_NAME) up -d

run:
	.venv/bin/uvicorn app.main:app --reload

down:
	docker compose -p $(PROJECT_NAME) down