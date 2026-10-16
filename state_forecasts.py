import csv
import math
import os
from pathlib import Path

os.environ["MPLCONFIGDIR"] = str(Path(__file__).resolve().parent / ".matplotlib_cache")

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _paths(project_root, state_folder_name):
    project_root = Path(project_root)
    state_folder = project_root / state_folder_name
    results_folder = state_folder / "results"
    tables_folder = state_folder / "tables"
    results_folder.mkdir(parents=True, exist_ok=True)
    tables_folder.mkdir(parents=True, exist_ok=True)
    return project_root, results_folder, tables_folder


def build_enrollment_forecast(project_root, state_folder_name, state_name, state_abbr, file_prefix):
    project_root, results_folder, tables_folder = _paths(project_root, state_folder_name)
    enrollment_file = project_root / "data/clean/enrollment_clean_updated.csv"

    history = []

    with enrollment_file.open(newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["State Abbreviation"] == state_abbr:
                period = row["Reporting Period"]
                month_label = period[:4] + "-" + period[4:]
                enrollment = int(row["Total Medicaid and CHIP Enrollment"])
                history.append([month_label, enrollment])

    history.sort()

    month_labels = [row[0] for row in history]
    values = [row[1] for row in history]

    future_months = []
    year = int(month_labels[-1][:4])
    month = int(month_labels[-1][5:])

    for _ in range(120):
        month += 1

        if month == 13:
            month = 1
            year += 1

        future_months.append(f"{year}-{month:02d}")

    covid_index = month_labels.index("2020-03")
    unwind_index = month_labels.index("2023-04")
    taper_index = month_labels.index("2024-07")

    x_rows = []

    for t, label in enumerate(month_labels):
        month_number = int(label[5:])
        row = [1, t, max(0, t - covid_index), max(0, t - unwind_index), max(0, t - taper_index)]

        for m in range(1, 12):
            row.append(1 if month_number == m else 0)

        x_rows.append(row)

    X = np.array(x_rows)
    y = np.array(values)

    coefficients = np.linalg.lstsq(X, y, rcond=None)[0]
    fitted = X @ coefficients
    policy_errors = y - fitted
    policy_std = math.sqrt(float(np.sum((policy_errors - policy_errors.mean()) ** 2) / (len(policy_errors) - 1)))

    policy_forecast = []
    policy_lower = []
    policy_upper = []

    for step, label in enumerate(future_months, start=1):
        t = len(month_labels) + step - 1
        month_number = int(label[5:])
        row = [1, t, max(0, t - covid_index), max(0, t - unwind_index), max(0, t - taper_index)]

        for m in range(1, 12):
            row.append(1 if month_number == m else 0)

        forecast_value = np.array(row) @ coefficients
        interval = 1.96 * policy_std * math.sqrt(step)
        policy_forecast.append(round(float(forecast_value)))
        policy_lower.append(max(0, round(float(forecast_value - interval))))
        policy_upper.append(round(float(forecast_value + interval)))

    table_path = tables_folder / f"{file_prefix}_enrollment_forecast_monthly.csv"

    with table_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Month",
            "Prophet-Style Policy Changepoint Regression",
            "Policy Lower Bound",
            "Policy Upper Bound",
        ])

        for i, month_label in enumerate(future_months):
            writer.writerow([month_label, policy_forecast[i], policy_lower[i], policy_upper[i]])

    history_x = list(range(len(history)))
    forecast_x = list(range(len(history), len(history) + len(future_months)))
    all_labels = month_labels + future_months
    tick_positions = []
    tick_labels = []

    for i, label in enumerate(all_labels):
        if label.endswith("-01"):
            tick_positions.append(i)
            tick_labels.append(label[:4])

    plt.figure(figsize=(15, 8))
    plt.plot(history_x, values, color="black", marker="o", markersize=2.2, linewidth=2.2, label="Historical data")
    plt.fill_between(forecast_x, policy_lower, policy_upper, color="firebrick", alpha=0.12)
    plt.plot(forecast_x, policy_forecast, color="firebrick", marker="o", markersize=2.2, linestyle="--", linewidth=1.8, label="Prophet-style policy changepoint forecast")
    plt.axvline(covid_index, color="gray", linestyle=":", label="2020-03 COVID continuous enrollment")
    plt.axvline(unwind_index, color="darkorange", linestyle=":", label="2023-04 unwinding")
    plt.axvline(taper_index, color="purple", linestyle=":", label="2024-07 taper point")
    plt.axvline(len(history) - 1, color="black", linestyle="-.", alpha=0.6, label="Forecast starts")
    plt.title(f"{state_name} Medicaid + CHIP Enrollment Forecast: Prophet-Style Policy Changepoint Model")
    plt.xlabel("Month")
    plt.ylabel("Medicaid + CHIP Enrollment")
    plt.xticks(tick_positions, tick_labels, rotation=45)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    chart_path = results_folder / f"{file_prefix}_enrollment_forecast_monthly.png"
    plt.savefig(chart_path, dpi=200)
    plt.close()

    notes = f"""Data scope: Medicaid + CHIP combined.
CHIP expenditure = MCHIP + MCHIP 20% + separate CHIP (including its reported administration).
Medicaid expenditure = MAP, excluding Medicaid ADM. These are reported net expenditures.
{state_name} Enrollment Forecast Model

Model included:
Prophet-style policy changepoint regression

Why this model is used:
{state_name} enrollment has monthly observations, so a Prophet-style model is
appropriate because it can use the monthly time series and allow trend changes
around major policy events.

Prophet-style policy changepoint regression:
This model is inspired by Prophet's changepoint idea. It adds separate trend
terms after major Medicaid policy dates:
- 2020-03: COVID continuous enrollment begins
- 2023-04: Medicaid unwinding begins
- 2024-07: later unwinding/taper point

Policy model residual standard deviation:
Prophet-style policy changepoint regression = {round(policy_std):,}
"""

    notes_path = results_folder / f"{file_prefix}_enrollment_forecast_notes.txt"
    notes_path.write_text(notes)

    return table_path, chart_path, notes_path


def build_expenditure_forecast(project_root, state_folder_name, state_name, state_abbr, file_prefix):
    project_root, results_folder, tables_folder = _paths(project_root, state_folder_name)
    expenditure_file = project_root / "data/clean/expenditure_clean_medicaid_chip_total.csv"

    years, values = _read_expenditures(expenditure_file, state_abbr)
    future_years = [years[-1] + i for i in range(1, 11)]

    alpha = 0.60
    beta = 0.30
    phi = 0.85
    level = values[0]
    trend = values[1] - values[0]
    holt_errors = []

    for actual_value in values[1:]:
        predicted_value = level + phi * trend
        holt_errors.append(actual_value - predicted_value)
        old_level = level
        level = alpha * actual_value + (1 - alpha) * predicted_value
        trend = beta * (level - old_level) + (1 - beta) * phi * trend

    average_error = sum(holt_errors) / len(holt_errors)
    holt_std = math.sqrt(sum((error - average_error) ** 2 for error in holt_errors) / (len(holt_errors) - 1))

    forecast = []
    lower = []
    upper = []

    for step in range(1, 11):
        trend_multiplier = sum(phi ** i for i in range(1, step + 1))
        forecast_value = level + trend_multiplier * trend
        interval = 1.96 * holt_std * math.sqrt(step)
        forecast.append(round(forecast_value))
        lower.append(round(forecast_value - interval))
        upper.append(round(forecast_value + interval))

    table_path = tables_folder / f"{file_prefix}_expenditure_forecast_annual.csv"
    _write_expenditure_table(table_path, "Holt-Damped Trend Exponential Smoothing", "Holt", future_years, forecast, lower, upper)

    chart_path = results_folder / f"{file_prefix}_expenditure_forecast_annual.png"
    _draw_expenditure_chart(
        chart_path,
        f"{state_name} Medicaid + CHIP Expenditure Forecast: Holt-Damped Trend Model",
        years,
        values,
        future_years,
        forecast,
        lower,
        upper,
        "royalblue",
        "Holt-damped trend",
    )

    notes = f"""Data scope: Medicaid + CHIP combined.
CHIP expenditure = MCHIP + MCHIP 20% + separate CHIP (including its reported administration).
Medicaid expenditure = MAP, excluding Medicaid ADM. These are reported net expenditures.
{state_name} Expenditure Forecast Model

Model included:
Holt-damped trend exponential smoothing

Expenditure data:
Annual {state_name} Medicaid and CHIP Total Net Expenditures Total Computable, FY{years[0]} to FY{years[-1]}.

Why this model is used:
{state_name} expenditure data have one observation per fiscal year, so there are
far fewer data points than the monthly enrollment series. Holt-damped trend
exponential smoothing is used because it gives a simple, interpretable trend
forecast while damping long-run growth instead of extrapolating an aggressive
straight-line trend.

Model settings:
alpha = {alpha}
beta = {beta}
phi = {phi}

Model residual standard deviation:
Holt-damped trend = ${round(holt_std):,}
"""

    notes_path = results_folder / f"{file_prefix}_expenditure_forecast_notes.txt"
    notes_path.write_text(notes)

    return table_path, chart_path, notes_path


def build_expenditure_policy_forecast(project_root, state_folder_name, state_name, state_abbr, file_prefix):
    project_root, results_folder, tables_folder = _paths(project_root, state_folder_name)
    expenditure_file = project_root / "data/clean/expenditure_clean_medicaid_chip_total.csv"

    years, values = _read_expenditures(expenditure_file, state_abbr)
    future_years = [years[-1] + i for i in range(1, 11)]
    covid_index = years.index(2020)
    unwind_index = years.index(2023)
    taper_index = years.index(2024)

    x_rows = []

    for t, _year in enumerate(years):
        x_rows.append([1, t, max(0, t - covid_index), max(0, t - unwind_index), max(0, t - taper_index)])

    X = np.array(x_rows)
    y = np.array(values)
    coefficients = np.linalg.lstsq(X, y, rcond=None)[0]
    fitted = X @ coefficients
    policy_errors = y - fitted
    policy_std = math.sqrt(float(np.sum((policy_errors - policy_errors.mean()) ** 2) / (len(policy_errors) - 1)))

    forecast = []
    lower = []
    upper = []

    for step, _year in enumerate(future_years, start=1):
        t = len(years) + step - 1
        row = [1, t, max(0, t - covid_index), max(0, t - unwind_index), max(0, t - taper_index)]
        forecast_value = np.array(row) @ coefficients
        interval = 1.96 * policy_std * math.sqrt(step)
        forecast.append(round(float(forecast_value)))
        lower.append(round(float(forecast_value - interval)))
        upper.append(round(float(forecast_value + interval)))

    table_path = tables_folder / f"{file_prefix}_expenditure_policy_changepoint_forecast_annual.csv"
    _write_expenditure_table(table_path, "Prophet-Style Policy Changepoint Regression", "Policy", future_years, forecast, lower, upper)

    chart_path = results_folder / f"{file_prefix}_expenditure_policy_changepoint_forecast_annual.png"
    _draw_expenditure_chart(
        chart_path,
        f"{state_name} Medicaid + CHIP Expenditure Forecast: Prophet-Style Policy Changepoint Model",
        years,
        values,
        future_years,
        forecast,
        lower,
        upper,
        "firebrick",
        "Policy changepoint forecast",
        show_policy_lines=True,
    )

    notes = f"""Data scope: Medicaid + CHIP combined.
CHIP expenditure = MCHIP + MCHIP 20% + separate CHIP (including its reported administration).
Medicaid expenditure = MAP, excluding Medicaid ADM. These are reported net expenditures.
{state_name} Expenditure Forecast Model

Model included:
Prophet-style policy changepoint regression

Expenditure data:
Annual {state_name} Medicaid and CHIP Total Net Expenditures Total Computable, FY{years[0]} to FY{years[-1]}.

Why this model is included:
This model is included as an additional {state_name} expenditure forecast using
the same Prophet-style policy changepoint logic as the enrollment forecast. The
expenditure data are annual, so policy dates are converted to fiscal years.

Policy changepoints:
- FY2020: COVID continuous enrollment begins
- FY2023: Medicaid unwinding begins
- FY2024: later unwinding/taper point

Important modeling note:
Because expenditure has only one observation per fiscal year, this model has
fewer data points than the monthly enrollment model. It is useful for comparing
policy-driven trend assumptions, but it should be interpreted with more caution
than the monthly enrollment changepoint forecast.

Policy model residual standard deviation:
Prophet-style policy changepoint regression = ${round(policy_std):,}
"""

    notes_path = results_folder / f"{file_prefix}_expenditure_policy_changepoint_forecast_notes.txt"
    notes_path.write_text(notes)

    return table_path, chart_path, notes_path


def _read_expenditures(expenditure_file, state_abbr):
    history = []

    with expenditure_file.open(newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["State Abbreviation"] == state_abbr:
                year = int(row["Year"])
                expenditure = int(row["Medicaid and CHIP Total Net Expenditures Total Computable"])
                history.append([year, expenditure])

    history.sort()
    return [row[0] for row in history], [row[1] for row in history]


def _write_expenditure_table(table_path, forecast_name, bound_prefix, future_years, forecast, lower, upper):
    with table_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Fiscal Year", forecast_name, f"{bound_prefix} Lower Bound", f"{bound_prefix} Upper Bound"])

        for i, year in enumerate(future_years):
            writer.writerow([year, forecast[i], lower[i], upper[i]])


def _draw_expenditure_chart(chart_path, title, years, values, future_years, forecast, lower, upper, color, label, show_policy_lines=False):
    history_y = [value / 1_000_000_000 for value in values]
    forecast_y = [value / 1_000_000_000 for value in forecast]
    lower_y = [value / 1_000_000_000 for value in lower]
    upper_y = [value / 1_000_000_000 for value in upper]

    plt.figure(figsize=(13, 7))
    plt.plot(years, history_y, color="black", marker="o", linewidth=2.2, label="Historical data")
    plt.fill_between(future_years, lower_y, upper_y, color=color, alpha=0.12)
    plt.plot(future_years, forecast_y, color=color, marker="o", linestyle="--", linewidth=1.8, label=label)

    if show_policy_lines:
        plt.axvline(2020, color="gray", linestyle=":", label="FY2020 COVID continuous enrollment")
        plt.axvline(2023, color="darkorange", linestyle=":", label="FY2023 unwinding")
        plt.axvline(2024, color="purple", linestyle=":", label="FY2024 later unwinding/taper")

    plt.axvline(years[-1], color="black", linestyle="-.", alpha=0.6, label="Forecast starts")
    plt.title(title)
    plt.xlabel("Fiscal Year")
    plt.ylabel("Total Computable Expenditures, Billions of Dollars")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(chart_path, dpi=200)
    plt.close()
