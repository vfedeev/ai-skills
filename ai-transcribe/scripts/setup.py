#!/usr/bin/env python3
"""
AI-Transcribe: Pre-configuration script
Run once on first launch to set up environment.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
CONFIG_FILE = SKILL_DIR / "config.env"

def colored(text, color):
    colors = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "end": "\033[0m"}
    return f"{colors.get(color, '')}{text}{colors['end']}"

def find_env_file():
    """Find .env file with GROQ_API_KEY"""
    candidates = [
        Path.home() / ".env",
        Path.home() / ".hermes" / ".env",
        Path.home() / ".hermes" / "env",
        Path(".env"),
    ]
    for f in candidates:
        if f.exists() and "GROQ_API_KEY" in f.read_text():
            return str(f)
    if os.environ.get("GROQ_API_KEY"):
        return "environment"
    return None

def check_command(cmd):
    """Check if command exists"""
    return shutil.which(cmd) is not None

def check_python_package(pkg):
    """Check if Python package is installed"""
    try:
        __import__(pkg)
        return True
    except ImportError:
        return False

def main():
    print("=== AI-Transcribe: Pre-configuration ===\n")

    config = {}

    # --- Step 1: Groq API Key ---
    print("--- Step 1: Groq API Key ---")
    env_path = find_env_file()
    if env_path:
        print(colored(f"✓ Found GROQ_API_KEY in: {env_path}", "green"))
        config["ENV_PATH"] = env_path
    else:
        print(colored("GROQ_API_KEY not found.", "yellow"))
        print("\nOptions:")
        print("  1) Get free key at https://console.groq.com/keys")
        print("  2) Use OpenAI API (if you have key)")
        print("  3) Skip for now (configure later)")
        key = input("\nEnter Groq API key (or press Enter to skip): ").strip()
        if key:
            env_file = Path.home() / ".env"
            with open(env_file, "a") as f:
                f.write(f"\nGROQ_API_KEY={key}\n")
            print(colored(f"✓ Saved to {env_file}", "green"))
            config["ENV_PATH"] = str(env_file)
        else:
            print(colored("⚠ Skipping. Configure GROQ_API_KEY later.", "yellow"))

    # --- Step 2: ffmpeg ---
    print("\n--- Step 2: ffmpeg ---")
    if check_command("ffmpeg"):
        ver = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        print(colored(f"✓ ffmpeg installed: {ver.stdout.splitlines()[0]}", "green"))
        config["HAS_FFMPEG"] = "true"
    else:
        print(colored("ffmpeg not found.", "yellow"))
        install = input("Install ffmpeg? (y/n): ").strip().lower()
        if install == "y":
            print(colored("Install manually:", "yellow"))
            print("  Ubuntu/Debian: sudo apt install ffmpeg")
            print("  macOS: brew install ffmpeg")
            print("  Arch: sudo pacman -S ffmpeg")
            print("  Windows: https://ffmpeg.org/download.html"
            config["HAS_FFMPEG"] = "true"
        else:
            print(colored("⚠ Video processing will not work without ffmpeg.", "yellow"))
            config["HAS_FFMPEG"] = "false"

    # --- Step 3: ffprobe ---
    print("\n--- Step 3: ffprobe ---")
    if check_command("ffprobe"):
        print(colored("✓ ffprobe installed", "green"))
        config["HAS_FFPROBE"] = "true"
    else:
        print(colored("⚠ ffprobe not found. Large file processing may be inaccurate.", "yellow"))
        config["HAS_FFPROBE"] = "false"

    # --- Step 4: Python requests ---
    print("\n--- Step 4: Python requests ---")
    if check_python_package("requests"):
        print(colored("✓ requests installed", "green"))
    else:
        install = input("Install Python requests? (y/n): ").strip().lower()
        if install == "y":
            subprocess.run([sys.executable, "-m", "pip", "install", "--user", "requests"], check=True)
            print(colored("✓ requests installed", "green"))
        else:
            print(colored("⚠ Install manually: pip install requests", "yellow"))

    # --- Step 5: Interviewer config ---
    print("\n--- Step 5: Interviewer config ---")
    if CONFIG_FILE.exists():
        existing = dict(line.split("=", 1) for line in CONFIG_FILE.read_text().splitlines()
                       if "=" in line and not line.startswith("#"))
        if "INTERVIEWER_NAME" in existing:
            print(colored(f"✓ Existing config: {existing['INTERVIEWER_NAME']} ({existing['INTERVIEWER_ROLE']})", "green"))
            config.update(existing)
        else:
            while True:
                name = input("Interviewer name (e.g. Vladimir): ").strip()
                if name and all(c.isalpha() or c.isspace() for c in name):
                    config["INTERVIEWER_NAME"] = name
                    break
                print(colored("Invalid name. Use letters and spaces only.", "red"))
            while True:
                role = input("Interviewer role (e.g. designer): ").strip()
                if role and all(c.isalpha() or c.isspace() for c in role):
                    config["INTERVIEWER_ROLE"] = role
                    break
                print(colored("Invalid role. Use letters and spaces only.", "red"))
    else:
        while True:
            name = input("Interviewer name (e.g. Vladimir): ").strip()
            if name and all(c.isalpha() or c.isspace() for c in name):
                config["INTERVIEWER_NAME"] = name
                break
            print(colored("Invalid name. Use letters and spaces only.", "red"))
        while True:
            role = input("Interviewer role (e.g. designer): ").strip()
            if role and all(c.isalpha() or c.isspace() for c in role):
                config["INTERVIEWER_ROLE"] = role
                break
            print(colored("Invalid role. Use letters and spaces only.", "red"))

    # --- Step 6: STT Model ---
    print("\n--- Step 6: STT Model ---")
    if "STT_MODEL" in config:
        print(colored(f"✓ Existing model: {config['STT_MODEL']}", "green"))
    else:
        print("Available models:")
        print("  1) whisper-large-v3 (recommended, Groq)")
        print("  2) whisper-large-v3-turbo (faster)")
        print("  3) whisper-medium (smaller)")
        print("  4) gpt-4o-transcribe (OpenAI, paid)")
        choice = input("Select model (1-4, or Enter for default): ").strip()
        models = {"2": "whisper-large-v3-turbo", "3": "whisper-medium", "4": "gpt-4o-transcribe"}
        config["STT_MODEL"] = models.get(choice, "whisper-large-v3")

    # --- Step 7: API URL ---
    print("\n--- Step 7: API URL ---")
    if config["STT_MODEL"] == "gpt-4o-transcribe":
        config["API_URL"] = "https://api.openai.com/v1/audio/transcriptions"
    else:
        config["API_URL"] = "https://api.groq.com/openai/v1/audio/transcriptions"
    print(f"Using: {config['API_URL']}")

    # --- Step 8: Temp directory ---
    print("\n--- Step 8: Temp directory ---")
    if Path("/tmp").exists() and os.access("/tmp", os.W_OK):
        config["TEMP_DIR"] = "/tmp"
        print(colored("✓ Using /tmp", "green"))
    else:
        temp = Path.home() / ".cache" / "ai-transcribe"
        temp.mkdir(parents=True, exist_ok=True)
        config["TEMP_DIR"] = str(temp)
        print(colored(f"⚠ Using fallback: {temp}", "yellow"))

    # --- Save config ---
    print("\n--- Saving config ---")
    with open(CONFIG_FILE, "w") as f:
        f.write("# AI-Transcribe configuration\n")
        f.write(f"# Generated: {__import__('datetime').datetime.now()}\n\n")
        for key, val in config.items():
            f.write(f"{key}={val}\n")

    # Restrict permissions (only owner can read/write)
    import stat
    CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    
    print(colored(f"✓ Config saved to: {CONFIG_FILE}", "green"))
    print("\n=== Configuration complete ===")
    print(f"\nSummary:")
    print(f"  Name: {config.get('INTERVIEWER_NAME', 'not set')} ({config.get('INTERVIEWER_ROLE', 'not set')})")
    print(f"  Model: {config.get('STT_MODEL', 'not set')}")
    print(f"  API: {config.get('API_URL', 'not set')}")
    print(f"  ffmpeg: {config.get('HAS_FFMPEG', 'not set')}")
    print(f"  ffprobe: {config.get('HAS_FFPROBE', 'not set')}")
    print(f"  Temp: {config.get('TEMP_DIR', 'not set')}")

if __name__ == "__main__":
    main()
