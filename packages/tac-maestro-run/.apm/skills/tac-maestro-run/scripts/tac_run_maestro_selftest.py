#!/usr/bin/env python3
"""Maestro selftest runner.

Builds the debug APK, installs it on the target device, runs Maestro flows,
collects logcat, and triggers bug-document generation on failure.

Usage:
    python tac-skills/tac-maestro-run/scripts/tac_run_maestro_selftest.py --device-id <id> [options]

Cross-platform: works on Windows, Linux, macOS.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_FLOW_PATH = os.path.join("persistent-assets", "automated-testing", "_baseline", "flows")
DEFAULT_RESULT_DIR = os.path.join("build", "maestro-results")
DEFAULT_APK_PATH = os.path.join("app", "build", "outputs", "apk", "debug", "app-debug.apk")
DEFAULT_APP_PACKAGE = "com.aicoding.appstore"
DEFAULT_LOGCAT_TAGS = [
    "DefaultInstaller",
    "DownloadDemoActivity",
    "DemoInstallCallbackAdapter",
    "AppStoreHome",
    "HomeDownloadController",
    "DownloadCoordinator",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def step(name: str) -> None:
    """Print a step banner to stdout."""
    print(f"==> {name}", flush=True)


def run_cmd(args: list[str], *, check: bool = True, capture: bool = False,
            warn_on_fail: bool = False) -> subprocess.CompletedProcess:
    """Run a subprocess command with unified error handling.

    Args:
        args: Command and arguments.
        check: Raise on non-zero exit code (default True).
        capture: Capture stdout/stderr instead of inheriting.
        warn_on_fail: Print warning instead of raising on failure.
    """
    try:
        result = subprocess.run(
            args,
            check=check,
            capture_output=capture,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result
    except subprocess.CalledProcessError as exc:
        if warn_on_fail:
            print(f"WARNING: {' '.join(args)} exited with code {exc.returncode}", flush=True)
            return exc  # type: ignore[return-value]  # caller checks warn_on_fail
        raise
    except FileNotFoundError as exc:
        command = args[0] if args else "<empty>"
        raise FileNotFoundError(
            f"Command not found: {command}. Check PATH or pass the explicit tool path."
        ) from exc


def gradlew_cmd() -> str:
    """Return the platform-appropriate Gradle wrapper command."""
    if platform.system() == "Windows":
        return ".\\gradlew.bat"
    return "./gradlew"


def maestro_cmd(explicit_path: str = "") -> str:
    """Return the platform-appropriate Maestro command."""
    if explicit_path:
        return explicit_path
    env_path = os.environ.get("MAESTRO_BIN", "").strip()
    if env_path:
        return env_path
    if platform.system() == "Windows":
        for candidate in ("maestro.bat", "maestro.cmd", "maestro.exe", "maestro"):
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        return "maestro.bat"
    return shutil.which("maestro") or "maestro"


def check_report_failed(report_path: str) -> bool:
    """Return True if the JUnit report is missing or contains failures/errors."""
    if not os.path.isfile(report_path):
        return True
    try:
        tree = ET.parse(report_path)
        root = tree.getroot()
        # Search for any <failure> or <error> element anywhere in the tree
        for elem in root.iter():
            if elem.tag in ("failure", "error"):
                return True
        return False
    except ET.ParseError:
        return True


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def do_build(skip: bool) -> None:
    """Build the debug APK via Gradle."""
    if skip:
        return
    step("Build debug APK")
    run_cmd([gradlew_cmd(), ":app:assembleDebug"])


def do_install(device_id: str, apk_path: str, skip: bool) -> None:
    """Install the debug APK onto the target device."""
    if skip:
        return
    if not os.path.isfile(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")
    step("Install debug APK")
    run_cmd(["adb", "-s", device_id, "install", "-r", apk_path])


def do_clear_app_data(device_id: str, package: str) -> None:
    """Clear app data on the target device."""
    step("Clear app data")
    run_cmd(["adb", "-s", device_id, "shell", "pm", "clear", package])


def do_uninstall_package(device_id: str, package: str) -> None:
    """Uninstall a package from the target device (non-fatal if not installed)."""
    step(f"Uninstall target package {package}")
    run_cmd(["adb", "-s", device_id, "uninstall", package],
            check=False, warn_on_fail=True)


def do_clear_logcat(device_id: str) -> None:
    """Clear logcat buffer on the target device."""
    step("Clear logcat")
    run_cmd(["adb", "-s", device_id, "logcat", "-c"])


def do_start_activity(device_id: str, activity: str) -> None:
    """Start a specific Activity on the target device via adb."""
    step(f"Start activity {activity}")
    run_cmd(["adb", "-s", device_id, "shell", "am", "start", "-n", activity])


def do_run_maestro(device_id: str, flow_path: str, report_path: str,
                   result_dir: str, maestro_path: str = "") -> int:
    """Run Maestro flows. Returns 0 on success, 1 on failure."""
    step("Run Maestro flows")
    result = run_cmd(
        [
            maestro_cmd(maestro_path),
            f"--device={device_id}",
            "test",
            "--format", "junit",
            "--output", report_path,
            "--test-output-dir", result_dir,
            flow_path,
        ],
        check=False,
    )
    if result.returncode != 0:
        print(f"WARNING: Maestro exited with code {result.returncode}", flush=True)
        return 1
    return 0


def do_collect_logcat(device_id: str, result_dir: str,
                      tags: list[str]) -> None:
    """Dump filtered logcat to a file in the result directory."""
    step("Collect logcat")
    logcat_path = os.path.join(result_dir, "logcat.txt")
    cmd = ["adb", "-s", device_id, "logcat", "-d", "-s"] + tags
    result = run_cmd(cmd, capture=True, check=False)
    Path(logcat_path).write_text(result.stdout or "", encoding="utf-8")


def do_create_bug(result_dir: str, device_id: str, flow_path: str,
                  apk_path: str, output_dir: str) -> None:
    """Invoke the bug-document generator script."""
    step("Create local Bug document")
    # Resolve the co-located bug script relative to this script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(script_dir, "tac_create_bug_from_maestro_result.py")
    run_cmd([
        sys.executable, script,
        "--result-dir", result_dir,
        "--device-id", device_id,
        "--flow-path", flow_path,
        "--apk-path", apk_path,
        "--output-dir", output_dir,
    ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Maestro selftest on a connected Android device.",
    )
    parser.add_argument("--device-id", required=True,
                        help="adb device serial (from `adb devices`).")
    parser.add_argument("--flow-path", default=DEFAULT_FLOW_PATH,
                        help="Path to Maestro flow file or directory.")
    parser.add_argument("--result-dir", default=DEFAULT_RESULT_DIR,
                        help="Directory to store Maestro results.")
    parser.add_argument("--apk-path", default=DEFAULT_APK_PATH,
                        help="Path to the debug APK.")
    parser.add_argument("--app-package", default=DEFAULT_APP_PACKAGE,
                        help="Application package name (for pm clear).")
    parser.add_argument("--start-activity", default="",
                        help="Activity component to launch (e.g. com.pkg/.MyActivity).")
    parser.add_argument("--uninstall-package", default="",
                        help="Package to uninstall before test (e.g. target demo app).")
    parser.add_argument("--logcat-tags", nargs="*", default=DEFAULT_LOGCAT_TAGS,
                        help="Logcat tags to filter (space-separated).")
    parser.add_argument("--bug-output-dir", default=os.path.join("doc", "issues"),
                        help="Directory for generated Bug documents.")
    parser.add_argument("--clear-app-data", action="store_true",
                        help="Clear app data before test.")
    parser.add_argument("--skip-build", action="store_true",
                        help="Skip Gradle build step.")
    parser.add_argument("--skip-install", action="store_true",
                        help="Skip APK install step.")
    parser.add_argument("--maestro-path", default="",
                        help="Explicit Maestro executable path. Overrides MAESTRO_BIN/PATH lookup.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    os.makedirs(args.result_dir, exist_ok=True)

    # Build & install
    do_build(args.skip_build)
    do_install(args.device_id, args.apk_path, args.skip_install)

    # Pre-test preparation
    if args.clear_app_data:
        do_clear_app_data(args.device_id, args.app_package)

    if args.uninstall_package:
        do_uninstall_package(args.device_id, args.uninstall_package)

    do_clear_logcat(args.device_id)

    if args.start_activity:
        do_start_activity(args.device_id, args.start_activity)

    # Execute Maestro
    report_path = os.path.join(args.result_dir, "report.xml")
    exit_code = do_run_maestro(args.device_id, args.flow_path,
                               report_path, args.result_dir,
                               args.maestro_path)

    # Collect logcat (always, regardless of pass/fail)
    do_collect_logcat(args.device_id, args.result_dir, args.logcat_tags)

    # Check report for failures even if Maestro returned 0
    if check_report_failed(report_path):
        exit_code = 1

    # On failure, generate a Bug document
    if exit_code != 0:
        do_create_bug(args.result_dir, args.device_id, args.flow_path,
                      args.apk_path, args.bug_output_dir)
        sys.exit(1)

    print(f"Maestro selftest passed. Results: {args.result_dir}", flush=True)


if __name__ == "__main__":
    main()
