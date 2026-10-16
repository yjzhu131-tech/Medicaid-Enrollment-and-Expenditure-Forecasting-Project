import csv
from pathlib import Path


raw_file = Path("data/raw/enrollment/pi-dataset-july-2026-release.csv")
clean_file = Path("data/clean/enrollment_clean_updated.csv")

columns_to_keep = [
    "State Abbreviation",
    "State Name",
    "Reporting Period",
    "State Expanded Medicaid",
    "Total Medicaid Enrollment",
    "Total CHIP Enrollment",
    "Total Medicaid and CHIP Enrollment",
]

clean_rows = []

with raw_file.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        # Keep updated records only.
        if row["Preliminary or Updated"] != "U":
            continue

        # Keep June 2017 and later.
        if int(row["Reporting Period"]) < 201706:
            continue

        clean_row = []
        for column in columns_to_keep:
            clean_row.append(row[column])

        clean_rows.append(clean_row)

clean_file.parent.mkdir(parents=True, exist_ok=True)

with clean_file.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(columns_to_keep)
    writer.writerows(clean_rows)

print(f"Saved {len(clean_rows)} rows to {clean_file}")
