# Use an official Python image as a base
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install PDM
RUN pip install --no-cache-dir pdm

# Copy the project files to the container
COPY . .

# Ensure PDM is used as the package manager
RUN pdm config python.use_venv true

# Install project dependencies using PDM
RUN pdm install

# Set the entry point for the container
CMD ["pdm", "run", "python", "app/main.py"]
