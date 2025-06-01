# Use an official Python 3.11 slim image as a parent image
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files and to run in unbuffered mode
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install Poetry
# Pinning Poetry version for stability. You can adjust if a newer version is preferred and tested.
RUN pip install poetry==1.8.3

# Configure Poetry to install dependencies into the system's site-packages, not a virtualenv within the container.
# Docker itself provides the isolation.
RUN poetry config virtualenvs.create false

# Copy only pyproject.toml first to allow lock file generation.
COPY pyproject.toml ./

# Generate a lock file based on the current pyproject.toml and Python 3.11 environment
# This will create a poetry.lock file in the WORKDIR (/app)
RUN poetry lock --no-update

# Install project dependencies using Poetry.
# This will use the poetry.lock file generated in the previous step.
RUN poetry install -vvv --no-interaction --no-ansi --no-root

# Copy the rest of the application's source code into the container
COPY . .

# Expose the port the ADK web server will run on.
EXPOSE 8079

# Define the default command to run when the container starts.
CMD ["poetry", "run", "adk", "web", "src/agents", "--host", "0.0.0.0", "--port", "8079"]
