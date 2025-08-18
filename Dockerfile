FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    bash \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -g 1000 agent && \
    useradd -u 1000 -g agent -m -s /bin/bash agent

# Copy only the package files needed for installation
COPY pyproject.toml /tmp/
COPY nkd_agents/ /tmp/nkd_agents/

# Install the package
WORKDIR /tmp
RUN pip install --no-cache-dir -e .

# Create workspace directory and switch to non-root user
RUN mkdir -p /workspace && chown agent:agent /workspace
USER agent
WORKDIR /workspace

# Default command  
CMD ["python", "-m", "nkd_agents.cli.cli"]