import os
import shutil
import subprocess
from pathlib import Path

from .config import console


async def run_sandbox() -> None:
    """Run the agent in a sandboxed Docker container with current directory mounted"""

    # Check if docker is available
    docker_path = shutil.which("docker")
    console.print(f"[dim]Debug: Docker path found: {docker_path}[/dim]")
    if not docker_path:
        console.print(
            "[bold red]Error:[/bold red] Docker is not installed or not in PATH."
        )
        console.print("Please install Docker to use the sandbox feature.")
        console.print("Visit: https://docs.docker.com/get-docker/")
        return

    # Check if API key is available
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        console.print(
            "[bold yellow]Warning:[/bold yellow] ANTHROPIC_API_KEY environment variable is not set."
        )
        console.print("The agent may not function properly without an API key.")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response not in ["y", "yes"]:
            console.print("Aborted.")
            return

    # Get current working directory
    cwd = Path.cwd()
    console.print(f"[bold blue]Starting sandbox with directory:[/bold blue] {cwd}")
    if api_key:
        console.print(f"[dim]API Key: {'*' * (len(api_key) - 4) + api_key[-4:]}[/dim]")

    # Check if the nkd_agents image exists
    result = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}", "nkd_agents"],
        capture_output=True,
        text=True,
    )

    if "nkd_agents:latest" not in result.stdout:
        console.print(
            "[yellow]nkd_agents Docker image not found. Building it now...[/yellow]"
        )

        # Find the Dockerfile (should be in the repo root)
        dockerfile_path = Path(__file__).parent.parent.parent / "Dockerfile"
        if not dockerfile_path.exists():
            console.print(
                "[bold red]Error:[/bold red] Dockerfile not found in repository root."
            )
            return

        # Build the image
        build_cmd = [
            "docker",
            "build",
            "-t",
            "nkd_agents:latest",
            "-f",
            str(dockerfile_path),
            str(dockerfile_path.parent),
        ]

        console.print(f"[dim]Running: {' '.join(build_cmd)}[/dim]")
        build_result = subprocess.run(build_cmd)

        if build_result.returncode != 0:
            console.print(
                "[bold red]Error:[/bold red] Failed to build nkd_agents image."
            )
            return

        console.print("[green]Successfully built nkd_agents image![/green]")

    # Run the container with current directory mounted
    run_cmd = [
        "docker",
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
        "--cap-add", "CHOWN",
        "--cap-add", "DAC_OVERRIDE", 
        "--cap-add", "FOWNER",
        "--cap-add", "SETGID",
        "--cap-add", "SETUID",  # Add only necessary capabilities
        "nkd_agents:latest",
        "nkd_agents",
        "code",  # Run the code agent using the console script
    ]

    console.print("[bold green]Starting sandboxed agent...[/bold green]")
    console.print(
        "[dim]Your current directory is mounted at /workspace in the container.[/dim]"
    )
    console.print("[dim]Press Ctrl+C to exit the sandbox.[/dim]\n")

    try:
        subprocess.run(run_cmd)
    except KeyboardInterrupt:
        console.print("\n[bold blue]Exiting sandbox...[/bold blue]")
