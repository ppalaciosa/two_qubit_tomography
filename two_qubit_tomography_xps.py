# -*- coding: utf-8 -*-
"""
two_qubit_tomography_xps.py

Automated multi-stage measurement routine for Newport XPS systems, using pre-defined position combinations.

- Reads a file with position combinations for four stages (e.g., motion.txt).
- Moves all stages to each combination, then automates GUI measurement (UQD or similar).
- Saves results and motor positions for each run.
- No range/step logic: everything is table-driven from your input file.

Place screenshots (e.g., csv_file_tag.png, save_file_dialog.png, etc.) in a 'screenshots/' folder
and run from your project root.
"""

import sys
from pathlib import Path

# Make the nested newportxpslib folder importable as top-level 'newportxpslib'
sys.path.insert(0, str(Path(__file__).parent / "newportxps_control"))

import pyautogui as pag
import pygetwindow as gw
from pathlib import Path
from time import sleep, time
from datetime import datetime

from newportxpslib.xps_session import XPSMotionSession
from newportxpslib.controller_interface import initialize_groups, home_groups
from newportxpslib.xps_config import load_full_config, load_user_credentials

# -------------------------------
# Exception for GUI automation errors, e.g. mouse interference or template match fail
class MouseInterferenceError(Exception):
    pass

# -------------------------------
# GUI click helper (safe, robust)
def safe_click(
    image_path, offset_x=0, offset_y=0, retries=3, delay=1,
    confidence=0.8, post_confirm_image=None, post_confirm_timeout=3
):
    """
    Robustly clicks an image on screen using pyautogui, with optional confirmation.
    Returns True if successful; False if not found or failed after retries.

    Args:
        image_path: Path to image file to find and click.
        offset_x, offset_y: Offsets from center of found image (for fine adjustment).
        retries: Number of attempts before giving up.
        delay: Seconds to wait between retries.
        confidence: Template match threshold.
        post_confirm_image: (Optional) Path to image that must appear after click.
        post_confirm_timeout: How long to wait for post-confirm image.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"[Error] Image file not found: {image_path}")
        return False

    max_mouse_tries = 3
    mouse_failures = 0
    start_time = time()

    for attempt in range(1, retries + 1):
        if time() - start_time > 5:
            raise MouseInterferenceError(f"Clicking '{image_path.name}' took too long.")

        try:
            box = pag.locateOnScreen(str(image_path), confidence=confidence)
            if not box:
                print(f"[Warning] '{image_path.name}' not found (attempt {attempt}/{retries})")
                sleep(delay)
                continue

            left, top, width, height = box
            x = left + width // 2 + offset_x
            y = top + height // 2 + offset_y

            print(f"[Click] {image_path.name} at ({x},{y})")
            pag.moveTo(x, y, duration=0.2)
            sleep(0.1)
            before = pag.position()
            pag.click()
            sleep(0.2)
            after = pag.position()

            # Abort if the user moves the mouse during automation
            if abs(before[0] - after[0]) > 5 or abs(before[1] - after[1]) > 5:
                mouse_failures += 1
                print(f"[Warning] Mouse moved externally ({mouse_failures}/{max_mouse_tries})")
                if mouse_failures >= max_mouse_tries:
                    raise MouseInterferenceError("Too much mouse interference.")
                sleep(delay)
                continue

            # If post-confirm image is requested, wait for it
            if post_confirm_image:
                t0 = time()
                while time() - t0 < post_confirm_timeout:
                    if pag.locateOnScreen(str(post_confirm_image), confidence=confidence):
                        return True
                    sleep(0.2)
                print(f"[Warning] '{post_confirm_image.name}' never appeared.")
                return False

            return True

        except Exception as e:
            print(f"[Error] While handling '{image_path.name}': {type(e).__name__}: {e}")
        sleep(delay)

    print(f"[Error] Could not click '{image_path.name}' after {retries} tries.")
    return False

# -------------------------------
# Load stage combinations from file
def load_combinations(file_path, n_stages):
    """
    Loads combinations and (optionally) labels from a motion file.
    Supports both:
        pos1, pos2, pos3, pos4
        pos1, pos2, pos3, pos4, Label
    Returns: list of (positions_list, label_or_None)
    Skips lines that are invalid, blank, or commented (#).
    """
    combos = []
    with open(file_path, "r") as f:
        for line in f:
            # Skip blank/comment lines
            if not line.strip() or line.strip().startswith("#"):
                continue
            parts = [x.strip() for x in line.strip().split(",")]
            if len(parts) < n_stages:
                print(f"[Warning] Skipping invalid line: {line.strip()}")
                continue
            try:
                positions = [float(x) for x in parts[:n_stages]]
            except ValueError:
                print(f"[Warning] Skipping invalid line: {line.strip()}")
                continue
            label = parts[n_stages] if len(parts) > n_stages else None
            combos.append((positions, label))
    return combos

# -------------------------------
# Main measurement routine
def measurement(session: XPSMotionSession, combinations_file, iteration_time, description):
    """
    Main experiment logic for table-driven tomography:
    - Loads all combos (and optional labels).
    - For each: moves stages, triggers the UQD GUI to save data, waits for requested time.
    - Skips combos if the move fails (out of range, hardware not ready, etc).
    - At the end, returns all stages to their logical zero (set with --set-zero in newportxps_control).

    Args:
        session: XPSMotionSession object (handles hardware connection and logic)
        combinations_file: Path to motion.txt or similar
        iteration_time: Data acquisition time per point (seconds)
        description: Description string for output directory
    """
    if len(session.stages) != 4:
        raise ValueError("two_qubit_tomography_xps.py requires exactly 4 stages.")
    # Number of stages we’re driving:
    n_stages = len(session.stages)

    # Setting up the XPS unit
    print("Loading XPS config and credentials...")
    load_user_credentials()
    load_full_config()
    print("Initializing and homing all XPS groups (one time)...")
    initialize_groups(session.xps)
    home_groups(session.xps, force_home=True)
    print("XPS system ready for motion!")

    combos = load_combinations(combinations_file, n_stages)
    if not combos:
        print(f"No valid combinations found in {combinations_file}")
        return

    # Prepare output directory for UQD CSV files
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    data_dir = Path(__file__).parent / "saved_data" / f"{timestamp}_{description}"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Activate UQD window
    try:
        uqd_win = gw.getWindowsWithTitle(
            "UQD Logic 16 Correlation Viewer  - V0.35 - 21.04.2021")[0]
        uqd_win.activate()
        sleep(1.5)
    except Exception:
        print("UQD window not found!")
        return

    # Timing parameters for GUI automation (tweak as needed)
    wait_initial_move = 2
    wait_write_filename = 5
    wait_while_running = 0.3
    wait_before_stop_collect = 1

    screenshots_dir = Path(__file__).parent / "screenshots"

    for idx, (combo, label) in enumerate(combos, 1):
        # Clean label for filename: replace spaces, decimal points, etc.
        if label and label.strip():
            clean_label = label.replace(" ", "_").replace(".", "-")
            filename = f"{clean_label}.csv"
        else:
            # Fallback: use old combo pattern (replace . with -)
            filename = f"combo{idx:03d}.csv"
        current_set = data_dir / filename

        # 1. Move all stages (zero-offsets, range, and errors handled by the library)
        move_ok = session.move_motors(*combo)
        if move_ok is False:
            print(f"[Warning] Skipping '{filename}' due to move error (out of range or not ready).")
            continue
        sleep(wait_initial_move)

        # 2. GUI: click csv_file_tag
        if not safe_click(screenshots_dir / "csv_file_tag.png", offset_x=200):
            print("Aborting: 'csv_file_tag' icon not found.")
            return

        # 3. Wait for save dialog (give plenty of time)
        t0 = time()
        timeout = 15
        while time() - t0 < timeout:
            try:
                if pag.locateOnScreen(str(screenshots_dir / "save_file_dialog.png"), confidence=0.8):
                    break
            except Exception:
                pass
            sleep(0.5)
        else:
            print("Save dialog did not appear after clicking CSV tag.")
            return

        # 4. In the filename field: select all, delete, write new file name
        pag.hotkey('ctrl', 'a')
        pag.press('delete')
        pag.write(str(current_set))
        sleep(wait_write_filename)

        # 5. Tab + Enter to confirm save
        pag.press('tab')
        sleep(0.3)
        pag.press('enter')
        sleep(1.0)

        # 6. Wait for and click Start button
        if not pag.locateOnScreen(str(screenshots_dir / "start_data_collect.png"), confidence=0.8):
            print("Start button not visible.")
            return

        if not safe_click(
            screenshots_dir / "start_data_collect.png",
            post_confirm_image=screenshots_dir / "stop_data_collect.png",
            post_confirm_timeout=5
        ):
            print("Failed to click Start or it did not toggle to Stop.")
            return

        print(f"[Info] {filename}: Data collection started.")
        sleep(0.5)

        # 7. Wait for measurement (provided by user)
        t_measure = time()
        while time() - t_measure <= iteration_time:
            sleep(wait_while_running)

        print("End of data taking.")
        sleep(wait_before_stop_collect)

        # 8. Wait for and click Stop button
        if not pag.locateOnScreen(str(screenshots_dir / "stop_data_collect.png"), confidence=0.8):
            print("Stop button not visible. Was Start ever pressed?")
            return

        if not safe_click(
            screenshots_dir / "stop_data_collect.png",
            confidence=0.9,
            post_confirm_image=screenshots_dir / "start_data_collect.png",
            post_confirm_timeout=5
        ):
            print("Stop button clicked but Start never reappeared.")
            return

        print("Stop clicked, idle state restored.")

    # At the end: Return all stages to logical zero position 
    # (handled via library/config zero offsets)
    print("Returning all stages to their configured zero positions.")
    session.move_motors(0.0, 0.0, 0.0, 0.0)
    sleep(2)
    print("All stages returned to zero.")

    print("Measurement loop complete ✅")

# -------------------------------
if __name__ == "__main__":
    # Always use four stages (IDs 1-4 by default, or adjust if your config uses different names/order)
    session = XPSMotionSession(stages=[1, 2, 3, 4], verbose=True)
    # Arguments: session, combinations_file, iteration_time (seconds), description
    measurement(
        session,
        "motion.txt",                    # Path to combinations file
        10,                              # Measurement duration at each point (seconds)
        "my_table_run"                   # Description for output directory
    )
    session.close()