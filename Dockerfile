FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

# Add uv to PATH early
ENV PATH="/root/.local/bin:${PATH}"

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Use existing pwuser (uid/gid 1000) from Playwright base image
RUN usermod -l agent -d /home/agent pwuser && \
    groupmod -n agent pwuser && \
    mv /home/pwuser /home/agent 2>/dev/null || true

# Copy only the package files needed for installation
COPY pyproject.toml /tmp/
COPY nkd_agents/ /tmp/nkd_agents/

# Install the package using uv with CLI and web dependencies
WORKDIR /tmp
RUN uv pip install --system ".[cli]"

# Create workspace directory and switch to non-root user
RUN mkdir -p /workspace && chown agent:agent /workspace
USER agent
WORKDIR /workspace

# Default command  
CMD ["nkd"]