import csv
import os
from collections import defaultdict
from pathlib import Path

os.environ["MPLCONFIGDIR"] = str(Path(__file__).resolve().parent / ".matplotlib_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


def build_per_enrollee_spending_chart(project_root, state_folder_name, state_name, state_abbr, file_prefix):
    project_root = Path(project_root)
    state_folder = project_root / state_folder_name
    enrollment_file = project_root / "data/clean/enrollment_clean_updated.csv"
    expenditure_file = project_root / "data/clean/expenditure_clean_medicaid_chip_total.csv"
    results_folder = state_folder / "results"
    tables_folder = state_folder / "tables"
    results_folder.mkdir(parents=True, exist_ok=True)
    tables_folder.mkdir(parents=True, exist_ok=True)

    annual_expenditures = {}
    monthly_enrollment_by_year = defaultdict(list)

    with expenditure_file.open(newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["State Abbreviation"] == state_abbr:
                year = int(row["Year"])
                expenditure = int(row["Medicaid and CHIP Total Net Expenditures Total Computable"])
                annual_expenditures[year] = expenditure

    with enrollment_file.open(newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["State Abbreviation"] == state_abbr:
                period = row["Reporting Period"]
                year = int(period[:4]) + (int(period[4:]) >= 10)
                enrollment = int(row["Total Medicaid and CHIP Enrollment"])
                monthly_enrollment_by_year[year].append(enrollment)

    rows = []

    for year in sorted(annual_expenditures):
        enrollment_values = monthly_enrollment_by_year.get(year, [])

        if not enrollment_values:
            continue

        average_enrollment = sum(enrollment_values) / len(enrollment_values)
        per_enrollee_spending = annual_expenditures[year] / average_enrollment
        data_coverage = "Full fiscal year" if len(enrollment_values) == 12 else f"{len(enrollment_values)} months"

        rows.append([
            year,
            annual_expenditures[year],
            round(average_enrollment),
            len(enrollment_values),
            round(per_enrollee_spending, 2),
            data_coverage,
        ])

    table_path = tables_folder / f"{file_prefix}_per_enrollee_spending_annual.csv"

    with table_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Fiscal Year",
            "Annual Medicaid and CHIP Total Net Expenditures Total Computable",
            "Average Monthly Medicaid and CHIP Enrollment",
            "Enrollment Months Available",
            "Annual Spending Per Average Enrollee",
            "Enrollment Data Coverage",
        ])
        writer.writerows(rows)

    years = [row[0] for row in rows]
    per_enrollee = [row[4] for row in rows]

    plt.figure(figsize=(12, 7))
    plt.plot(years, per_enrollee, color="seagreen", marker="o", linewidth=2.3)

    for year, value in zip(years, per_enrollee):
        offset = max(per_enrollee) * 0.012
        plt.text(year, value + offset, f"${value:,.0f}", ha="center", va="bottom", fontsize=8)

    plt.title(f"{state_name} Medicaid + CHIP Annual Spending per Average Enrollee")
    plt.xlabel("Federal Fiscal Year")
    plt.ylabel("Annual Spending per Average Enrollee")
    plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"${x:,.0f}"))
    plt.xticks(years, [str(year) + ("*" if len(monthly_enrollment_by_year[year]) < 12 else "") for year in years], rotation=45)
    plt.ylim(min(per_enrollee) * 0.96, max(per_enrollee) * 1.08)
    plt.grid(True, axis="y", alpha=0.3)
    plt.figtext(0.01, 0.01, "* Partial fiscal-year enrollment coverage; see table for months available.", fontsize=8)
    plt.tight_layout()

    chart_path = results_folder / f"{file_prefix}_per_enrollee_spending_annual.png"
    plt.savefig(chart_path, dpi=200)
    plt.close()

    notes = f"""Data scope: Medicaid + CHIP combined.
CHIP expenditure = MCHIP + MCHIP 20% + separate CHIP (including its reported administration).
Medicaid expenditure = MAP, excluding Medicaid ADM. These are reported net expenditures.
{state_name} Medicaid + CHIP Annual Spending per Average Enrollee

Calculation:
Annual spending per average enrollee =
annual Medicaid and CHIP Total Net Expenditures Total Computable / average monthly Medicaid and CHIP enrollment for the same federal fiscal year.

Data used:
- Expenditure: {state_name} annual Medicaid and CHIP Total Net Expenditures Total Computable.
- Enrollment: {state_name} monthly Total Medicaid and CHIP Enrollment.

Years shown:
{rows[0][0]} to {rows[-1][0]}.

Important note:
Enrollment data are monthly and expenditure data are annual. This chart uses the
average monthly enrollment within each federal fiscal year (October–September) as the denominator. Years with fewer
than 12 enrollment months are included but marked in the table.
"""

    notes_path = results_folder / f"{file_prefix}_per_enrollee_spending_notes.txt"
    notes_path.write_text(notes)

    return table_path, chart_path, notes_path
