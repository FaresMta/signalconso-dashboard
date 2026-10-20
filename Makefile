# Shortcuts (Linux/macOS). On Windows, run the commands from the README directly.
.PHONY: install data run test

install:
	pip install -r requirements-dev.txt

data:
	python scripts/download_data.py
	python scripts/build_data.py

run:
	streamlit run app.py

test:
	python -m pytest
