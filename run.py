#!/usr/bin/env python3
"""Aetos Orchestrator Manager - Interactive deployment and management tool."""

import os
import platform
import subprocess
import sys
from pathlib import Path

# Colors for output
RED = "\033[0;31m"
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
YELLOW = "\033[1;33m"
NC = "\033[0m"  # No Color

# Script directory
SCRIPT_DIR = Path(__file__).parent.resolve()
SCRIPTS_PATH = SCRIPT_DIR / "scripts"


def fix_line_endings():
    """
    Fix line endings for shell scripts (convert CRLF to LF).
    Works on both WSL/Linux and macOS.
    """
    try:
        for script in SCRIPTS_PATH.glob("*.sh"):
            # Read the file in binary mode
            with open(script, "rb") as f:
                content = f.read()

            # Check if it has Windows line endings
            if b"\r\n" in content:
                print(f"{YELLOW}Fixing line endings for {script.name}...{NC}")
                # Replace CRLF with LF
                fixed_content = content.replace(b"\r\n", b"\n")

                # Write back
                with open(script, "wb") as f:
                    f.write(fixed_content)
    except Exception as e:
        print(f"{YELLOW}Warning: Could not fix line endings: {e}{NC}")


def make_scripts_executable():
    """Make all shell scripts executable."""
    try:
        for script in SCRIPTS_PATH.glob("*.sh"):
            os.chmod(script, 0o755)
    except Exception as e:
        print(f"{YELLOW}Warning: Could not set executable permissions: {e}{NC}")


def clear_screen():
    """Clear the terminal screen."""
    os.system("clear" if os.name != "nt" else "cls")


def show_menu():
    """Display the main menu."""
    clear_screen()
    print(f"{BLUE}╔════════════════════════════════════════╗{NC}")
    print(f"{BLUE}║     Aetos Orchestrator Manager        ║{NC}")
    print(f"{BLUE}╚════════════════════════════════════════╝{NC}")
    print()
    print(f"{GREEN}1){NC} 🚀 Deploy and stream logs")
    print(f"{GREEN}2){NC} ▶️  Start function app")
    print(f"{GREEN}3){NC} ⏸️  Stop function app")
    print(f"{GREEN}4){NC} 📦 Deploy only")
    print(f"{GREEN}5){NC} 📋 Stream logs")
    print(f"{GREEN}6){NC} 🔧 Run fix script")
    print(f"{GREEN}7){NC} 🚪 Exit")
    print()
    choice = input(f"{YELLOW}Select an option [1-7]: {NC}")
    return choice.strip()


def run_script(script_name: str) -> int:
    """
    Run a shell script and return its exit code.

    Args:
        script_name: Name of the script file (e.g., "deploy.sh")

    Returns:
        Exit code from the script
    """
    script_path = SCRIPTS_PATH / script_name

    if not script_path.exists():
        print(f"{RED}Error: Script {script_name} not found at {script_path}{NC}")
        return 1

    try:
        # Use bash explicitly and pass the script as an argument
        result = subprocess.run(
            ["bash", str(script_path)],
            cwd=SCRIPT_DIR,
            check=False,
            env=os.environ.copy(),
        )
        return result.returncode
    except FileNotFoundError:
        print(
            f"{RED}Error: bash not found. Please ensure you're running in WSL or Linux.{NC}"
        )
        return 1
    except Exception as e:
        print(f"{RED}Error running script: {e}{NC}")
        return 1


def deploy_and_logs():
    """Deploy the orchestrator and stream logs."""
    print(f"{BLUE}Deploying orchestrator...{NC}")
    exit_code = run_script("deploy.sh")

    if exit_code != 0:
        print(f"{RED}Deployment failed!{NC}")
        input("Press Enter to return to menu...")
        return

    print()
    print(f"{BLUE}Waiting 10 seconds for function app to start...{NC}")
    import time

    time.sleep(10)

    print(f"{BLUE}Streaming logs...{NC}")
    run_script("logs.sh")


def start_function_app():
    """Start the function app."""
    print(f"{BLUE}Starting function app...{NC}")
    run_script("start.sh")
    print()
    input("Press Enter to return to menu...")


def stop_function_app():
    """Stop the function app."""
    print(f"{BLUE}Stopping function app...{NC}")
    run_script("stop.sh")
    print()
    input("Press Enter to return to menu...")


def deploy_only():
    """Deploy the orchestrator without streaming logs."""
    print(f"{BLUE}Deploying orchestrator...{NC}")
    run_script("deploy.sh")
    print()
    input("Press Enter to return to menu...")


def stream_logs():
    """Stream logs from the function app."""
    print(f"{BLUE}Streaming logs...{NC}")
    run_script("logs.sh")


def run_fix():
    """Run the fix script."""
    print(f"{BLUE}Running fix script...{NC}")
    exit_code = run_script("fix.sh")
    print()
    if exit_code == 0:
        print(f"{GREEN}Fix completed successfully!{NC}")
    else:
        print(f"{RED}Fix script encountered errors.{NC}")
    input("Press Enter to return to menu...")


def main():
    """Main application loop."""
    # Fix line endings and make scripts executable on startup
    print(f"{BLUE}Initializing...{NC}")
    fix_line_endings()
    make_scripts_executable()

    system = platform.system()
    if system == "Darwin":
        print(f"{GREEN}✓ Running on macOS{NC}")
    elif system == "Linux":
        print(f"{GREEN}✓ Running on Linux/WSL{NC}")
    else:
        print(f"{YELLOW}⚠ Running on {system} - scripts may not work correctly{NC}")

    import time

    time.sleep(1)

    while True:
        choice = show_menu()

        if choice == "1":
            deploy_and_logs()
        elif choice == "2":
            start_function_app()
        elif choice == "3":
            stop_function_app()
        elif choice == "4":
            deploy_only()
        elif choice == "5":
            stream_logs()
        elif choice == "6":
            run_fix()
        elif choice == "7":
            print(f"{GREEN}Goodbye!{NC}")
            sys.exit(0)
        else:
            print(f"{RED}Invalid option. Please try again.{NC}")
            import time

            time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{NC}")
        sys.exit(0)
    except Exception as e:
        print(f"{RED}Error: {e}{NC}")
        sys.exit(1)
