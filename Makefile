.PHONY: build up down restart logs clean pdm-install

# Build the Docker images
build:
	docker-compose build

# Start the services in the background
up:
	docker-compose up -d

# Stop the services
down:
	docker-compose down

# Restart the services
restart: down up

# View the logs of all services
logs:
	docker-compose logs -f

# Remove containers, networks, volumes, and images created by `up`
clean:
	docker-compose down -v
	docker system prune -f
	rm -rf ./uploads  # Optional: clean any local directory

# Install dependencies using PDM inside the Docker container
pdm-install:
	docker-compose run --rm app pdm install

# Enter the app container for interactive use
shell:
	docker-compose run --rm app /bin/sh

# Run the main application
run-app:
	docker-compose run --rm app pdm run python app/main.py

# Rebuild and run the services
rebuild: clean build up
