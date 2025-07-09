"""
run_experiment_and_process.py

Main orchestrator for a two-qubit tomography experiment:
- Moves Newport XPS stages as specified in a motion file.
- Automates data acquisition via your experiment code (two_qubit_tomography_xps.py).
- Optionally, processes all result CSVs to extract and average a specified column.

**This script requires `newportxps_control` in the project root and uses its XPS session logic.**
"""

import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "newportxps_control"))

# Import experiment's routines (must be in the same folder or PYTHONPATH)
from two_qubit_tomography_xps import measurement
from newportxpslib.xps_session import XPSMotionSession

# Import the averaging helper from your processing code.
from process_uqd_results import average_column_in_file  

def process_all_combos(data_folder, column_name, output_file="total_averages.csv"):
    """
    Process all *.csv files in data_folder (excluding summary files),
    compute the average for the specified column, and write results to output_file.

    Args:
        data_folder: Path to the folder containing result CSVs.
        column_name: The CSV column to average (as string).
        output_file: Output CSV for averages (default: total_averages.csv).
    """
    data_folder = Path(data_folder)
    all_files = sorted(Path(data_folder).glob("*.csv"))
    # Exclude summary/output files (which should not be included in the averages)
    csv_files = [f for f in all_files if f.name not in ["total_averages.csv", "position_report.csv"]]
    
    if not csv_files:
        print(f"No .csv files found in {data_folder}")
        return
    with open(Path(data_folder) / output_file, "w", newline="") as outcsv:
        import csv
        writer = csv.writer(outcsv)
        writer.writerow(["filename", f"avg_{column_name}"])
        for csv_file in csv_files:
            try:
                avg = average_column_in_file(csv_file, column_name)
                print(f"{csv_file.name}: {avg}")
                writer.writerow([csv_file.name, avg])
            except Exception as e:
                print(f"Warning: {csv_file.name}: {e}")

def main():
    """
    Main entry point for experiment orchestration:
    1. Parses CLI arguments for full experiment configuration.
    2. Runs the XPS measurement routine via `measurement`.
    3. Locates the output data folder.
    4. Optionally, post-processes all CSVs for the selected column.
    """
    parser = argparse.ArgumentParser(
        description="Run XPS experiment and postprocess the results.")
    parser.add_argument("--motion", type=str, required=True, 
        help="Path to motion file (e.g., motion.txt)")
    parser.add_argument("--stages", type=str, required=True, 
        help="Comma-separated list of stage IDs, e.g. 1,2,3,4")
    parser.add_argument("--wait", type=float, required=True, 
        help="Measurement time (seconds) per point")
    parser.add_argument("--desc", type=str, default="run", 
        help="Description for data output folder")
    parser.add_argument("--column", type=str, required=True, 
        help="Which column to average in postprocessing")
    parser.add_argument("--process", action="store_true", 
        help="Run postprocessing after measurement")
    parser.add_argument("--folder", type=str, 
        help="(Optional) Folder to process if not auto-detected.")

    args = parser.parse_args()

    # Parse the user-supplied list of stages (should be four for two-qubit tomography)
    stages = [int(x) for x in args.stages.split(",")]

    # --- 1. Run the XPS measurement routine
    session = XPSMotionSession(stages=stages, verbose=True)

    measurement(
        session,
        args.motion,
        args.wait,
        args.desc
    )
    session.close() # Always close the session to release the connection!

    # --- 2. Determine which folder to process (the latest with the given description)
    data_root = Path(__file__).parent / "saved_data"
    if args.folder:
        data_dir = Path(args.folder)
    else:
        # Find the most recent folder with the description
        # (If not specified, finds the most recent output folder with the given description.)
        matching = sorted(data_root.glob(f"*_{args.desc}"), 
                            key=lambda p: p.stat().st_mtime, 
                            reverse=True)
        if not matching:
            print(f"Could not find output folder for description '{args.desc}' in {data_root}")
            sys.exit(1)
        data_dir = matching[0]
        print(f"Processing folder: {data_dir}")

    # --- 3. Run postprocessing if requested
    if args.process:
        process_all_combos(data_dir, args.column)
        print(f"Results written to {data_dir}/total_averages.csv")
    else:
        print("Measurement done. (Use --process to postprocess averages.)")

if __name__ == "__main__":
    main()
