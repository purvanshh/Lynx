.PHONY: dev dev-build test evaluate demo clean

dev:
	docker compose up

dev-build:
	docker compose up --build

test:
	docker compose run --rm api python -m pytest tests/ -v --tb=short

evaluate:
	docker compose run --rm api python -m scripts.evaluate --in-process

demo:
	docker compose up --build -d
	@echo "Waiting for API to be healthy..."
	sleep 5
	@echo "Starting happy path scenario at 5x speed..."
	docker compose exec -d api python -m scripts.run_simulator \
		simulator/scenarios/happy_path.json \
		--api-url http://api:8000 \
		--speed 5.0
	@echo ""
	@echo "============================================"
	@echo "  Lynx is running!"
	@echo "  Dashboard:  http://localhost:3000"
	@echo "  API:        http://localhost:8000"
	@echo "  Docs:       http://localhost:8000/docs"
	@echo "============================================"
	@echo ""
	@echo "Happy path scenario playing at 5x speed..."
	@echo "Open the dashboard to watch confidence evolve."

clean:
	docker compose down -v
