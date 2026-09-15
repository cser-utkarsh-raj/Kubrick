#!/usr/bin/env python3
"""
Kubrick Studio Launcher - Personal Production-Ready Wrapper
============================================================
This script provides a one-click launch experience for Kubrick with:
- Automatic dependency checking
- FFmpeg validation
- Project directory management
- Error handling and logging
- Both CLI and GUI modes
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def log_info(msg: str) -> None:
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {msg}")

def log_success(msg: str) -> None:
    print(f"{Colors.GREEN}✓{Colors.RESET} {msg}")

def log_warning(msg: str) -> None:
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {msg}")

def log_error(msg: str) -> None:
    print(f"{Colors.RED}✗{Colors.RESET} {msg}")

def log_step(msg: str) -> None:
    print(f"\n{Colors.CYAN}{Colors.BOLD}→{Colors.RESET} {Colors.BOLD}{msg}{Colors.RESET}")

def check_python_version() -> bool:
    """Verify Python 3.11+"""
    if sys.version_info < (3, 11):
        log_error(f"Python 3.11+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        return False
    log_success(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_ffmpeg() -> bool:
    """Verify FFmpeg installation"""
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    
    if not ffmpeg_path:
        log_error("FFmpeg not found in PATH")
        log_info("Install from: https://ffmpeg.org/download.html")
        return False
    
    if not ffprobe_path:
        log_error("FFprobe not found (comes with FFmpeg)")
        return False
    
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
        version_line = result.stdout.split('\n')[0]
        log_success(f"FFmpeg: {version_line}")
    except subprocess.CalledProcessError:
        log_error("FFmpeg failed to run")
        return False
    
    return True

def check_kubrick_installation() -> bool:
    """Verify Kubrick is properly installed"""
    try:
        from kubrick import __version__
        log_success(f"Kubrick v{__version__} installed")
        return True
    except ImportError as e:
        log_error(f"Kubrick not installed: {e}")
        log_info("Run: pip install -e '.[all]'")
        return False

def check_pyside6() -> bool:
    """Check if PySide6 is available for GUI"""
    try:
        from PySide6.QtCore import qVersion
        log_success(f"PySide6 available (Qt {qVersion()})")
        return True
    except ImportError:
        log_warning("PySide6 not installed - GUI mode unavailable")
        log_info("Install with: pip install 'pyside6>=6.8'")
        return False

def check_faster_whisper() -> bool:
    """Check if faster-whisper is available for transcription"""
    try:
        import faster_whisper
        log_success("faster-whisper available (AI transcription enabled)")
        return True
    except ImportError:
        log_warning("faster-whisper not installed - AI features disabled")
        log_info("Install with: pip install 'faster-whisper>=1.2'")
        return False

def create_workspace_dir() -> Path:
    """Create/check workspace directory"""
    workspace = Path.home() / "KubrickProjects"
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        log_info(f"Created workspace: {workspace}")
    else:
        log_success(f"Workspace: {workspace}")
    return workspace

def run_cli_checks() -> bool:
    """Test CLI commands"""
    try:
        result = subprocess.run(["kubrick", "--help"], capture_output=True, text=True, check=True, timeout=5)
        if "Precision-first local video editing engine" in result.stdout:
            log_success("CLI commands working")
            return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        log_error("CLI commands not working")
        return False
    return False

def create_test_video(output_path: Path) -> bool:
    """Create a test video with silence for verification"""
    try:
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:duration=8",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3,apad=whole_dur=8",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        log_success(f"Test video created: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to create test video: {e}")
        return False

def run_end_to_end_test(workspace: Path) -> bool:
    """Run a complete end-to-end test"""
    log_step("Running end-to-end test...")
    
    test_input = workspace / "test_silence.mp4"
    test_output = workspace / "test_output.mp4"
    
    # Create test video
    if not create_test_video(test_input):
        return False
    
    # Run analysis
    log_info("Analyzing test video...")
    try:
        result = subprocess.run(
            ["kubrick", "analyze", str(test_input), "--profile", "natural"],
            capture_output=True, text=True, check=True, timeout=30
        )
        if "silences" in result.stdout:
            log_success("Analysis working")
            # Extract duration info
            import json
            data = json.loads(result.stdout)
            if data.get("silences"):
                log_info(f"  Found {len(data['silences'])} silence regions")
                log_info(f"  Will remove: {data['removed_duration']:.2f}s")
                log_info(f"  Output duration: {data['output_duration']:.2f}s")
        else:
            log_warning("Analysis output unexpected")
    except Exception as e:
        log_error(f"Analysis failed: {e}")
        return False
    
    # Run render
    log_info("Rendering edited video...")
    try:
        result = subprocess.run(
            ["kubrick", "render", str(test_input), str(test_output), "--profile", "natural"],
            capture_output=True, text=True, check=True, timeout=120
        )
        if test_output.exists():
            # Check duration
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                 "-of", "default=noprint_wrappers=1:nokey=1", str(test_output)],
                capture_output=True, text=True, check=True
            )
            duration = float(probe.stdout.strip())
            log_success(f"Render successful: {duration:.2f}s")
            
            # Cleanup
            test_input.unlink()
            test_output.unlink()
            return True
        else:
            log_error("Output file not created")
            return False
    except Exception as e:
        log_error(f"Render failed: {e}")
        return False

def main_menu():
    """Display main menu"""
    print("\n" + "="*60)
    print(f"{Colors.BOLD}{Colors.CYAN}  KUBRICK STUDIO - Personal Edition{Colors.RESET}")
    print("="*60)
    print(f"\n{Colors.BOLD}Options:{Colors.RESET}")
    print("  1. Launch GUI Editor")
    print("  2. Use CLI (command-line mode)")
    print("  3. Run System Diagnostics")
    print("  4. Quick Test (end-to-end)")
    print("  5. Open Workspace Folder")
    print("  0. Exit")
    print()

def launch_gui():
    """Launch the GUI application"""
    log_step("Launching Kubrick GUI...")
    try:
        from kubrick.ui.app import main as gui_main
        gui_main()
    except ImportError as e:
        log_error(f"GUI not available: {e}")
        log_info("Install PySide6: pip install 'pyside6>=6.8'")
        input("\nPress Enter to continue...")
    except Exception as e:
        log_error(f"GUI crashed: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to continue...")

def cli_mode():
    """Enter CLI interactive mode"""
    log_step("CLI Mode")
    print("\nAvailable commands:")
    print("  kubrick analyze <video> [--profile gentle|natural|tight]")
    print("  kubrick render <input> <output> [--profile natural]")
    print("  kubrick new-project <video> <output.kubrick.json>")
    print("  kubrick validate-project <project.kubrick.json>")
    print("  kubrick render-project <project.kubrick.json> <output.mp4>")
    print("\nType 'exit' to return to menu\n")
    
    while True:
        try:
            cmd = input(f"{Colors.CYAN}kubrick>{Colors.RESET} ").strip()
            if cmd.lower() in ('exit', 'quit', 'q'):
                break
            if cmd:
                args = cmd.split()
                result = subprocess.run(args, capture_output=False)
                if result.returncode != 0:
                    log_error(f"Command failed with code {result.returncode}")
        except KeyboardInterrupt:
            print()
            continue
        except Exception as e:
            log_error(str(e))

def run_diagnostics():
    """Run full system diagnostics"""
    log_step("Running System Diagnostics")
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("FFmpeg/FFprobe", check_ffmpeg),
        ("Kubrick Installation", check_kubrick_installation),
        ("PySide6 (GUI)", check_pyside6),
        ("faster-whisper (AI)", check_faster_whisper),
        ("CLI Commands", run_cli_checks),
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"Checking {name}...", end=" ")
        try:
            result = check_fn()
            results.append(result)
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
            results.append(False)
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}All checks passed! ({passed}/{total}){Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}Checks passed: {passed}/{total}{Colors.RESET}")
        log_warning("Some features may be limited")
    
    return all(results)

def open_workspace(workspace: Path):
    """Open workspace folder in file explorer"""
    log_step(f"Opening workspace: {workspace}")
    try:
        if sys.platform == 'win32':
            os.startfile(workspace)
        elif sys.platform == 'darwin':
            subprocess.run(['open', workspace], check=True)
        else:
            subprocess.run(['xdg-open', workspace], check=True)
        log_success("Workspace opened")
    except Exception as e:
        log_error(f"Could not open workspace: {e}")
        log_info(f"Path: {workspace.absolute()}")

def main():
    """Main entry point"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════╗")
    print("║           KUBRICK STUDIO LAUNCHER                     ║")
    print("║     Precision Video Editing - Personal Edition        ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    # Initial checks
    log_step("Initializing...")
    
    if not check_python_version():
        sys.exit(1)
    
    if not check_ffmpeg():
        sys.exit(1)
    
    if not check_kubrick_installation():
        sys.exit(1)
    
    workspace = create_workspace_dir()
    
    # Main loop
    while True:
        main_menu()
        try:
            choice = input(f"{Colors.CYAN}Select option [{Colors.BOLD}1{Colors.RESET}{Colors.CYAN}-{Colors.BOLD}5{Colors.RESET}{Colors.CYAN}, {Colors.BOLD}0{Colors.RESET}{Colors.CYAN} to exit]: {Colors.RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        
        if choice == '1':
            if check_pyside6():
                launch_gui()
        elif choice == '2':
            cli_mode()
        elif choice == '3':
            run_diagnostics()
            input("\nPress Enter to continue...")
        elif choice == '4':
            if run_end_to_end_test(workspace):
                print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed! Kubrick is ready.{Colors.RESET}")
            else:
                print(f"\n{Colors.RED}{Colors.BOLD}✗ Tests failed. Check diagnostics.{Colors.RESET}")
            input("\nPress Enter to continue...")
        elif choice == '5':
            open_workspace(workspace)
        elif choice == '0':
            print(f"\n{Colors.CYAN}Goodbye!{Colors.RESET}\n")
            break
        else:
            log_warning("Invalid option")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.CYAN}Interrupted. Goodbye!{Colors.RESET}\n")
        sys.exit(0)
    except Exception as e:
        log_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
