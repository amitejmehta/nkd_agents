# Multi-stage build for minimal runtime image
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY . /src
WORKDIR /src

# Install package and dependencies
RUN pip install --no-cache-dir -e .

# Runtime stage
FROM python:3.12-slim as runtime

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    bash \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -g 1000 agent && \
    useradd -u 1000 -g agent -m -s /bin/bash agent

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create workspace directory
RUN mkdir -p /workspace && chown agent:agent /workspace

# Switch to non-root user
USER agent
WORKDIR /workspace

# Set environment variables
ENV PYTHONPATH=/usr/local/lib/python3.12/site-packages
ENV PATH=/usr/local/bin:$PATH

# Default command
CMD ["python", "-m", "nkd_agents.cli", "code"]