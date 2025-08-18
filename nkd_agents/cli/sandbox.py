import os
import shutil
import subprocess
from pathlib import Path

from .config import console


async def run_sandbox() -> None:
    """Run the agent in a sandboxed Docker container with current directory mounted"""
    docker_path = shutil.which("docker")
    if not docker_path:
        console.print(
            "[bold red]Error:[/bold red] Docker is not installed or not in PATH."
        )
        console.print("Please install Docker to use the sandbox feature.")
        console.print("Visit: https://docs.docker.com/get-docker/")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        console.print(
            "[bold yellow]Warning:[/bold yellow] ANTHROPIC_API_KEY environment variable is not set."
        )
        console.print("The agent will not function properly without an API key.")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response not in ["y", "yes"]:
            console.print("Aborted.")
            return

    cwd = Path.cwd()
    console.print(f"[dim]Starting sandbox w/ cwd:[/dim] {cwd}")

    result = subprocess.run(
        [docker_path, "images", "--format", "{{.Repository}}:{{.Tag}}", "nkd_agents"],
        capture_output=True,
        text=True,
        env=os.environ,
    )

    if "nkd_agents:latest" not in result.stdout:
        console.print(
            "[yellow]nkd_agents Docker image not found. Building it now...[/yellow]"
        )

        dockerfile_path = Path(__file__).parent.parent.parent / "Dockerfile"
        if not dockerfile_path.exists():
            console.print(
                "[bold red]Error:[/bold red] Dockerfile not found in repository root."
            )
            return

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
            console.print(
                "[bold red]Error:[/bold red] Failed to build nkd_agents image."
            )
            return

        console.print("[green]Successfully built nkd_agents image![/green]")

    run_cmd = [
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

    try:
        subprocess.run(run_cmd, env=os.environ)
    except KeyboardInterrupt:
        console.print("\n[bold blue]Exiting sandbox...[/bold blue]")
