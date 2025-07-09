"""
process_uqd_results.py

Process a folder of UQD combo CSVs, extracting the average over a specified column
(e.g., "Pattern 01[counts]"), and summarize results in a new CSV.

Usage:
    python process_uqd_results.py <data_folder> <column_name>
    # Example:
    python process_uqd_results.py saved_data/2025-07-02-035725_my_table_run "Pattern 01[counts]"
"""

import sys
from pathlib import Path
import csv

def average_column_in_file(filepath, column_name):
    """Return average of column_name (as float) in given CSV file."""
    with open(filepath, newline='') as f:
        reader = csv.reader(f)
        # Skip until we find the header (usually line 3)
        for row in reader:
            if column_name in row:
                header = row
                break
        else:
            raise ValueError(f"Column {column_name} not found in {filepath}")

        col_idx = header.index(column_name)
        # Now, read rows of data
        values = []
        for row in reader:
            if len(row) <= col_idx:
                continue
            try:
                val = float(row[col_idx])
                values.append(val)
            except ValueError:
                continue
        if not values:
            raise ValueError(f"No values found for column {column_name} in {filepath}")
        return sum(values) / len(values)

def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    data_folder = Path(sys.argv[1])
    column_name = sys.argv[2]

    if not data_folder.is_dir():
        print(f"Error: {data_folder} is not a valid folder.")
        sys.exit(1)

    combo_files = sorted(data_folder.glob("combo*.csv"))
    if not combo_files:
        print(f"No combo*.csv files found in {data_folder}")
        sys.exit(1)

    output_file = data_folder / "combo_averages.csv"
    print(f"Processing {len(combo_files)} files...")

    with open(output_file, "w", newline='') as outcsv:
        writer = csv.writer(outcsv)
        writer.writerow(["filename", f"avg_{column_name}"])
        for csv_file in combo_files:
            try:
                avg = average_column_in_file(csv_file, column_name)
                print(f"{csv_file.name}: {avg}")
                writer.writerow([csv_file.name, avg])
            except Exception as e:
                print(f"Warning: {csv_file.name}: {e}")

    print(f"\nSummary written to: {output_file}")

if __name__ == "__main__":
    main()
