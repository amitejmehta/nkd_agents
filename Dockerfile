FROM python:3.12-alpine

# Add uv to PATH early
ENV PATH="/root/.local/bin:${PATH}"

# Install runtime dependencies and uv
RUN apk add --no-cache \
    bash \
    git \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Create non-root user
RUN addgroup -g 1000 agent && \
    adduser -u 1000 -G agent -D -s /bin/bash agent

# Copy only the package files needed for installation
COPY pyproject.toml /tmp/
COPY nkd_agents/ /tmp/nkd_agents/

# Install the package using uv with CLI dependencies
WORKDIR /tmp
RUN uv pip install --system ".[cli]"

# Create workspace directory and switch to non-root user
RUN mkdir -p /workspace && chown agent:agent /workspace
USER agent
WORKDIR /workspace

# Default command  
CMD ["nkd_agents"]