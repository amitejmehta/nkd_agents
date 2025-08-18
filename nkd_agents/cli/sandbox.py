import os
import shutil
import subprocess
from pathlib import Path

from .config import console


def _check_docker_available() -> str | None:
    """Check if Docker is available and return its path."""
    docker_path = shutil.which("docker")
    if not docker_path:
        console.print(
            "[bold red]Error:[/bold red] Docker is not installed or not in PATH."
        )
        console.print("Please install Docker to use the sandbox feature.")
        console.print("Visit: https://docs.docker.com/get-docker/")
        return None
    return docker_path


def _check_api_key() -> str | None:
    """Check if API key is available and get user confirmation if missing."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        console.print(
            "[bold yellow]Warning:[/bold yellow] ANTHROPIC_API_KEY environment variable is not set."
        )
        console.print("The agent will not function properly without an API key.")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response not in ["y", "yes"]:
            console.print("Aborted.")
            return None
    return api_key


def _check_image_exists(docker_path: str) -> bool:
    """Check if the nkd_agents Docker image exists."""
    result = subprocess.run(
        [docker_path, "images", "--format", "{{.Repository}}:{{.Tag}}", "nkd_agents"],
        capture_output=True,
        text=True,
        env=os.environ,
    )
    return "nkd_agents:latest" in result.stdout


def _build_docker_image(docker_path: str) -> bool:
    """Build the nkd_agents Docker image."""
    console.print(
        "[yellow]nkd_agents Docker image not found. Building it now...[/yellow]"
    )

    dockerfile_path = Path(__file__).parent.parent.parent / "Dockerfile"
    if not dockerfile_path.exists():
        console.print(
            "[bold red]Error:[/bold red] Dockerfile not found in repository root."
        )
        return False

    build_cmd = [
        docker_path,
        "build",
        "-t",
        "nkd_agents:latest",
        "-f",
        str(dockerfile_path),
        str(dockerfile_path.parent),
    ]

    console.print(f"[dim]Running: {' '.join(build_cmd)}[/dim]")
    build_result = subprocess.run(build_cmd, env=os.environ)

    if build_result.returncode != 0:
        console.print("[bold red]Error:[/bold red] Failed to build nkd_agents image.")
        return False

    console.print("[green]Successfully built nkd_agents image![/green]")
    return True


def _create_run_command(docker_path: str, cwd: Path, api_key: str) -> list[str]:
    """Create the Docker run command with all necessary parameters."""
    return [
        docker_path,
        "run",
        "--rm",  # Remove container when it exits
        "-it",  # Interactive with TTY
        "-v",
        f"{cwd}:/workspace",  # Mount current directory
        "--workdir",
        "/workspace",  # Set working directory
        "-e",
        f"ANTHROPIC_API_KEY={api_key}",  # Pass API key
        "--security-opt",
        "no-new-privileges:true",  # Security: prevent privilege escalation
        "--cap-drop",
        "ALL",  # Drop all capabilities
        "--cap-add",
        "CHOWN",
        "--cap-add",
        "DAC_OVERRIDE",
        "--cap-add",
        "FOWNER",
        "--cap-add",
        "SETGID",
        "--cap-add",
        "SETUID",  # Add only necessary capabilities
        "nkd_agents:latest",
    ]


async def run_sandbox() -> None:
    """Run the agent in a sandboxed Docker container with current directory mounted"""
    # Check Docker availability
    docker_path = _check_docker_available()
    if not docker_path:
        return

    # Check API key
    api_key = _check_api_key()
    if api_key is None:
        return

    cwd = Path.cwd()
    console.print(f"[dim]Starting sandbox w/ cwd:[/dim] {cwd}")

    # Ensure Docker image exists
    if not _check_image_exists(docker_path):
        if not _build_docker_image(docker_path):
            return

    # Run the container
    run_cmd = _create_run_command(docker_path, cwd, api_key)

    try:
        subprocess.run(run_cmd, env=os.environ)
    except KeyboardInterrupt:
        console.print("\n[bold blue]Exiting sandbox...[/bold blue]")
