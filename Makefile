.PHONY: setup run test whisper-setup

setup:
	python3.12 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"

run:
	.venv/bin/streamlit run app.py

test:
	.venv/bin/python -m pytest -q

whisper-setup:
	./scripts/setup_whisper.sh $(MODEL)
