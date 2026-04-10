.PHONY: run sync clean install

install:
	@echo "Installing uv..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "uv installed successfully!"
	@echo "Please run: source $$HOME/.cargo/bin/env"
	@echo "Or add to your shell profile: export PATH=\"\$$HOME/.cargo/bin:\$$PATH\""

run:
	uv run python main.py

sync:
	uv sync

clean:
	rm -rf .venv
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
