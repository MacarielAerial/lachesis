# Global Build Arguments
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

#
# Multi Stage: Dev Image
#
FROM python:3.12-slim-bookworm AS dev

# Arguments associated with the non-root user
ARG USERNAME
ARG USER_UID
ARG USER_GID

# Set environemntal variables
ENV POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_HOME=/home/${USERNAME}/poetry \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Add poetry executable to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Add the non-root user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    git-lfs

# Switch to the non-root user to install applications on the user level
USER ${USERNAME}

# Explicitly populate home directory variable
ENV HOME=/home/${USERNAME}

# Install poetry
RUN mkdir -p ${HOME}/poetry && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    poetry self add poetry-plugin-up

# Verify Poetry installation
RUN poetry --version

#
# Multi Stage: Bake Image
#

FROM python:3.12-slim-bookworm AS bake

# Arguments associated with the non-root user
ARG USERNAME
ARG USER_UID
ARG USER_GID

# Set environemntal variables
ENV POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_HOME=/home/${USERNAME}/poetry \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Add poetry executable to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Add the non-root user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# Install curl
RUN apt-get update && apt-get install -y \
    curl

# Switch to the non-root user to install applications on the user level
USER ${USERNAME}

# Explicitly populate home directory variable
ENV HOME=/home/${USERNAME}

# Install poetry
RUN mkdir -p ${HOME}/poetry && \
    curl -sSL https://install.python-poetry.org | python -

# Verify Poetry installation
RUN poetry --version

# Make working directory
RUN mkdir -p ${HOME}/app

# Copy source code and python dependency specification
COPY pyproject.toml poetry.lock README.md ${HOME}/app/
COPY src ${HOME}/app/src

# Set working directory
WORKDIR /home/${USERNAME}/app

# Install python dependencies in container
RUN poetry install --without dev

#
# Multi Stage: Runtime Image
#

FROM python:3.12-slim-bookworm AS runtime

# Reference build arguments
ARG USERNAME
ARG USER_UID
ARG USER_GID

# Prevent interactive prompts during package update
ENV DEBIAN_FRONTEND=noninteractive

# Add the non-root user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl

# Copy over baked environment
# Explicitly copy the otherwise ignore .venv folder
COPY --from=bake /home/${USERNAME}/app /home/${USERNAME}/app
COPY --from=bake /home/${USERNAME}/app/.venv /home/${USERNAME}/app/.venv

# Switch to the non-root user
USER ${USERNAME}

# Set working directory
WORKDIR /home/${USERNAME}/app

# Set executables in PATH
ENV PATH="/home/${USERNAME}/app/.venv/bin:$PATH"

# Expose the service port
EXPOSE 80

# Implement an health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/health-check || exit 1

# Auto start the fastapi service on start-up
ENTRYPOINT ["fastapi", "run", "src/lachesis/main.py", "--port", "80"]
