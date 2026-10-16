import csv
import math
import os
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
state_folder = project_root / "Nationalized"

os.environ["MPLCONFIGDIR"] = str(project_root / ".matplotlib_cache")

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


enrollment_file = project_root / "data/clean/enrollment_clean_updated.csv"
expenditure_file = project_root / "data/clean/expenditure_clean_medicaid_chip_total.csv"
results_folder = state_folder / "results"
tables_folder = state_folder / "tables"
results_folder.mkdir(parents=True, exist_ok=True)
tables_folder.mkdir(parents=True, exist_ok=True)


# --------------------------------
# 1. Read national monthly data
# --------------------------------

# Add all states together for each month.
enrollment_by_month = {}

with enrollment_file.open(newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        period = row["Reporting Period"]
        enrollment = int(row["Total Medicaid and CHIP Enrollment"])

        if period not in enrollment_by_month:
            enrollment_by_month[period] = 0

        enrollment_by_month[period] = enrollment_by_month[period] + enrollment

history = []

for period in sorted(enrollment_by_month):
    month_label = period[:4] + "-" + period[4:]
    history.append([month_label, enrollment_by_month[period]])

month_labels = [row[0] for row in history]
values = [row[1] for row in history]


# -------------------------
# 2. Read national expenditure data
# -------------------------

# Add all states together for each fiscal year.
expenditure_by_year = {}
# Match the enrollment reporting universe: 50 states plus DC, excluding territories.
with enrollment_file.open(newline="") as f:
    enrollment_states = {row["State Abbreviation"] for row in csv.DictReader(f)}

with expenditure_file.open(newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        if row["State Abbreviation"] not in enrollment_states:
            continue
        year = int(row["Year"])
        expenditure = int(row["Medicaid and CHIP Total Net Expenditures Total Computable"])

        if year not in expenditure_by_year:
            expenditure_by_year[year] = 0

        expenditure_by_year[year] = expenditure_by_year[year] + expenditure

expenditure_history = []

for year in sorted(expenditure_by_year):
    expenditure_history.append([year, expenditure_by_year[year]])

exp_years = [row[0] for row in expenditure_history]
exp_values = [row[1] for row in expenditure_history]


# -------------------------
# 3. Create future months
# -------------------------

future_months = []
last_month = month_labels[-1]
year = int(last_month[:4])
month = int(last_month[5:])

for i in range(120):
    month = month + 1

    if month == 13:
        month = 1
        year = year + 1

    future_months.append(f"{year}-{month:02d}")


# ------------------------
# 4. Create future years
# ------------------------

future_years = []
last_year = exp_years[-1]

for i in range(1, 11):
    future_years.append(last_year + i)


# -------------------------------
# 5. Enrollment model 1: Holt damped trend
# -------------------------------

# This model only uses the historical enrollment pattern.
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

holt_average_error = sum(holt_errors) / len(holt_errors)
holt_std = math.sqrt(
    sum((error - holt_average_error) ** 2 for error in holt_errors) / (len(holt_errors) - 1)
)

holt_forecast = []
holt_lower = []
holt_upper = []

for step in range(1, 121):
    trend_multiplier = 0

    for i in range(1, step + 1):
        trend_multiplier = trend_multiplier + phi ** i

    forecast_value = level + trend_multiplier * trend
    interval = 1.96 * holt_std * math.sqrt(step)
    holt_forecast.append(round(forecast_value))
    holt_lower.append(round(forecast_value - interval))
    holt_upper.append(round(forecast_value + interval))


# -----------------------------------------------
# 6. Enrollment model 2: Policy changepoint regression
# -----------------------------------------------

# This model allows the trend to change after major Medicaid policy dates.
covid_index = month_labels.index("2020-03")
unwind_index = month_labels.index("2023-04")
taper_index = month_labels.index("2024-07")

x_rows = []

for t, label in enumerate(month_labels):
    month_number = int(label[5:])

    row = [
        1,
        t,
        max(0, t - covid_index),
        max(0, t - unwind_index),
        max(0, t - taper_index),
    ]

    # Add month indicators for simple seasonality.
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

    row = [
        1,
        t,
        max(0, t - covid_index),
        max(0, t - unwind_index),
        max(0, t - taper_index),
    ]

    for m in range(1, 12):
        row.append(1 if month_number == m else 0)

    forecast_value = np.array(row) @ coefficients
    interval = 1.96 * policy_std * math.sqrt(step)
    policy_forecast.append(round(float(forecast_value)))
    policy_lower.append(round(float(forecast_value - interval)))
    policy_upper.append(round(float(forecast_value + interval)))


# ---------------------------------
# 7. Enrollment model 3: Recent 12-month trend
# ---------------------------------

# This model only uses the latest 12 months to estimate the newest trend.
recent_values = values[-12:]
recent_x = np.arange(12)
recent_coefficients = np.polyfit(recent_x, recent_values, 1)
recent_slope = recent_coefficients[0]
recent_intercept = recent_coefficients[1]
recent_fitted = recent_intercept + recent_slope * recent_x
recent_errors = recent_values - recent_fitted
recent_std = math.sqrt(float(np.sum((recent_errors - recent_errors.mean()) ** 2) / (len(recent_errors) - 1)))

recent_forecast = []
recent_lower = []
recent_upper = []

for step in range(1, 121):
    x = 11 + step
    forecast_value = recent_intercept + recent_slope * x
    interval = 1.96 * recent_std * math.sqrt(step)
    recent_forecast.append(round(float(forecast_value)))
    recent_lower.append(round(float(forecast_value - interval)))
    recent_upper.append(round(float(forecast_value + interval)))


# ----------------------------------------------
# 8. Expenditure model 1: Holt damped trend
# ----------------------------------------------

# Expenditure is annual, so this forecasts 10 future fiscal years.
exp_level = exp_values[0]
exp_trend = exp_values[1] - exp_values[0]
exp_holt_errors = []

for actual_value in exp_values[1:]:
    predicted_value = exp_level + phi * exp_trend
    exp_holt_errors.append(actual_value - predicted_value)

    old_level = exp_level
    exp_level = alpha * actual_value + (1 - alpha) * predicted_value
    exp_trend = beta * (exp_level - old_level) + (1 - beta) * phi * exp_trend

exp_holt_average_error = sum(exp_holt_errors) / len(exp_holt_errors)
exp_holt_std = math.sqrt(
    sum((error - exp_holt_average_error) ** 2 for error in exp_holt_errors) / (len(exp_holt_errors) - 1)
)

exp_holt_forecast = []
exp_holt_lower = []
exp_holt_upper = []

for step in range(1, 11):
    trend_multiplier = 0

    for i in range(1, step + 1):
        trend_multiplier = trend_multiplier + phi ** i

    forecast_value = exp_level + trend_multiplier * exp_trend
    interval = 1.96 * exp_holt_std * math.sqrt(step)
    exp_holt_forecast.append(round(forecast_value))
    exp_holt_lower.append(round(forecast_value - interval))
    exp_holt_upper.append(round(forecast_value + interval))


# --------------------------------------------------------
# 9. Expenditure model 2: Policy changepoint regression
# --------------------------------------------------------

# The policy dates are converted to fiscal years for annual expenditure data.
exp_covid_index = exp_years.index(2020)
exp_unwind_index = exp_years.index(2023)
exp_taper_index = exp_years.index(2024)

exp_x_rows = []

for t, year in enumerate(exp_years):
    row = [
        1,
        t,
        max(0, t - exp_covid_index),
        max(0, t - exp_unwind_index),
        max(0, t - exp_taper_index),
    ]

    exp_x_rows.append(row)

exp_X = np.array(exp_x_rows)
exp_y = np.array(exp_values)

exp_coefficients = np.linalg.lstsq(exp_X, exp_y, rcond=None)[0]
exp_fitted = exp_X @ exp_coefficients
exp_policy_errors = exp_y - exp_fitted
exp_policy_std = math.sqrt(float(np.sum((exp_policy_errors - exp_policy_errors.mean()) ** 2) / (len(exp_policy_errors) - 1)))

exp_policy_forecast = []
exp_policy_lower = []
exp_policy_upper = []

for step, year in enumerate(future_years, start=1):
    t = len(exp_years) + step - 1

    row = [
        1,
        t,
        max(0, t - exp_covid_index),
        max(0, t - exp_unwind_index),
        max(0, t - exp_taper_index),
    ]

    forecast_value = np.array(row) @ exp_coefficients
    interval = 1.96 * exp_policy_std * math.sqrt(step)
    exp_policy_forecast.append(round(float(forecast_value)))
    exp_policy_lower.append(round(float(forecast_value - interval)))
    exp_policy_upper.append(round(float(forecast_value + interval)))


# --------------------------------------------
# 10. Expenditure model 3: Recent 5-year trend
# --------------------------------------------

# Annual expenditure has fewer points, so use the latest 5 years instead of 12 months.
exp_recent_values = exp_values[-5:]
exp_recent_x = np.arange(5)
exp_recent_coefficients = np.polyfit(exp_recent_x, exp_recent_values, 1)
exp_recent_slope = exp_recent_coefficients[0]
exp_recent_intercept = exp_recent_coefficients[1]
exp_recent_fitted = exp_recent_intercept + exp_recent_slope * exp_recent_x
exp_recent_errors = exp_recent_values - exp_recent_fitted
exp_recent_std = math.sqrt(float(np.sum((exp_recent_errors - exp_recent_errors.mean()) ** 2) / (len(exp_recent_errors) - 1)))

exp_recent_forecast = []
exp_recent_lower = []
exp_recent_upper = []

for step in range(1, 11):
    x = 4 + step
    forecast_value = exp_recent_intercept + exp_recent_slope * x
    interval = 1.96 * exp_recent_std * math.sqrt(step)
    exp_recent_forecast.append(round(float(forecast_value)))
    exp_recent_lower.append(round(float(forecast_value - interval)))
    exp_recent_upper.append(round(float(forecast_value + interval)))


# -----------------------------------------
# 11. Save enrollment comparison forecast data
# -----------------------------------------

with (tables_folder / "national_enrollment_model_comparison_monthly.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Month",
        "Holt Damped Trend",
        "Holt Lower Bound",
        "Holt Upper Bound",
        "Policy Changepoint Regression",
        "Policy Lower Bound",
        "Policy Upper Bound",
        "Recent 12-Month Trend",
        "Recent Lower Bound",
        "Recent Upper Bound",
    ])

    for i, month_label in enumerate(future_months):
        writer.writerow([
            month_label,
            holt_forecast[i],
            holt_lower[i],
            holt_upper[i],
            policy_forecast[i],
            policy_lower[i],
            policy_upper[i],
            recent_forecast[i],
            recent_lower[i],
            recent_upper[i],
        ])


# ------------------------------------------
# 12. Save expenditure comparison forecast data
# ------------------------------------------

with (tables_folder / "national_expenditure_model_comparison_annual.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Fiscal Year",
        "Holt Damped Trend",
        "Holt Lower Bound",
        "Holt Upper Bound",
        "Policy Changepoint Regression",
        "Policy Lower Bound",
        "Policy Upper Bound",
        "Recent 5-Year Trend",
        "Recent Lower Bound",
        "Recent Upper Bound",
    ])

    for i, year in enumerate(future_years):
        writer.writerow([
            year,
            exp_holt_forecast[i],
            exp_holt_lower[i],
            exp_holt_upper[i],
            exp_policy_forecast[i],
            exp_policy_lower[i],
            exp_policy_upper[i],
            exp_recent_forecast[i],
            exp_recent_lower[i],
            exp_recent_upper[i],
        ])


# ---------------------------------------
# 13. Draw enrollment monthly model comparison plot
# ---------------------------------------

history_x = list(range(len(history)))
forecast_x = list(range(len(history), len(history) + len(future_months)))
all_labels = month_labels + future_months

plt.figure(figsize=(15, 8))
plt.plot(history_x, values, color="black", marker="o", markersize=2.2, linewidth=2.2, label="Historical data")
plt.fill_between(forecast_x, holt_lower, holt_upper, color="royalblue", alpha=0.12)
plt.fill_between(forecast_x, policy_lower, policy_upper, color="firebrick", alpha=0.12)
plt.fill_between(forecast_x, recent_lower, recent_upper, color="darkgreen", alpha=0.12)
plt.plot(forecast_x, holt_forecast, color="royalblue", marker="o", markersize=2.2, linestyle="--", linewidth=1.8, label="Holt damped trend")
plt.plot(forecast_x, policy_forecast, color="firebrick", marker="o", markersize=2.2, linestyle="--", linewidth=1.8, label="Policy changepoint regression")
plt.plot(forecast_x, recent_forecast, color="darkgreen", marker="o", markersize=2.2, linestyle="--", linewidth=1.8, label="Recent 12-month trend")

plt.axvline(covid_index, color="gray", linestyle=":", label="2020-03 COVID continuous enrollment")
plt.axvline(unwind_index, color="darkorange", linestyle=":", label="2023-04 unwinding")
plt.axvline(taper_index, color="purple", linestyle=":", label="2024-07 taper point")
plt.axvline(len(history) - 1, color="black", linestyle="-.", alpha=0.6, label="Forecast starts")

tick_positions = []
tick_labels = []

for i, label in enumerate(all_labels):
    if label.endswith("-01"):
        tick_positions.append(i)
        tick_labels.append(label[:4])

plt.title("National Medicaid + CHIP Enrollment Forecast: Monthly Model Comparison")
plt.xlabel("Month")
plt.ylabel("National Medicaid + CHIP Enrollment")
plt.xticks(tick_positions, tick_labels, rotation=45)
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(results_folder / "national_enrollment_model_comparison_monthly.png", dpi=200)
plt.close()


# --------------------------------------------
# 14. Draw enrollment policy changepoint model plot
# --------------------------------------------

plt.figure(figsize=(13, 7))
plt.plot(history_x, values, color="royalblue", marker="o", markersize=2.5, label="Historical")
plt.fill_between(forecast_x, policy_lower, policy_upper, color="lightcoral", alpha=0.25, label="95% range")
plt.plot(forecast_x, policy_forecast, color="firebrick", marker="o", markersize=2.5, linestyle="--", label="Policy changepoint forecast")

plt.axvline(covid_index, color="gray", linestyle=":", label="2020-03 COVID continuous enrollment")
plt.axvline(unwind_index, color="darkorange", linestyle=":", label="2023-04 unwinding")
plt.axvline(taper_index, color="purple", linestyle=":", label="2024-07 taper point")
plt.axvline(len(history) - 1, color="black", linestyle="-.", alpha=0.6, label="Forecast starts")

plt.title("National Medicaid + CHIP Enrollment Forecast: Policy Changepoint Model")
plt.xlabel("Month")
plt.ylabel("National Medicaid + CHIP Enrollment")
plt.xticks(tick_positions, tick_labels, rotation=45)
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(results_folder / "national_enrollment_policy_changepoint_forecast.png", dpi=200)
plt.close()


# --------------------------------------------
# 15. Draw expenditure annual model comparison
# --------------------------------------------

exp_history_y = [value / 1_000_000_000 for value in exp_values]
exp_holt_y = [value / 1_000_000_000 for value in exp_holt_forecast]
exp_policy_y = [value / 1_000_000_000 for value in exp_policy_forecast]
exp_recent_y = [value / 1_000_000_000 for value in exp_recent_forecast]
exp_holt_lower_y = [value / 1_000_000_000 for value in exp_holt_lower]
exp_holt_upper_y = [value / 1_000_000_000 for value in exp_holt_upper]
exp_policy_lower_y = [value / 1_000_000_000 for value in exp_policy_lower]
exp_policy_upper_y = [value / 1_000_000_000 for value in exp_policy_upper]
exp_recent_lower_y = [value / 1_000_000_000 for value in exp_recent_lower]
exp_recent_upper_y = [value / 1_000_000_000 for value in exp_recent_upper]

plt.figure(figsize=(13, 7))
plt.plot(exp_years, exp_history_y, color="black", marker="o", linewidth=2.2, label="Historical data")
plt.fill_between(future_years, exp_holt_lower_y, exp_holt_upper_y, color="royalblue", alpha=0.12)
plt.fill_between(future_years, exp_policy_lower_y, exp_policy_upper_y, color="firebrick", alpha=0.12)
plt.fill_between(future_years, exp_recent_lower_y, exp_recent_upper_y, color="darkgreen", alpha=0.12)
plt.plot(future_years, exp_holt_y, color="royalblue", marker="o", linestyle="--", linewidth=1.8, label="Holt damped trend")
plt.plot(future_years, exp_policy_y, color="firebrick", marker="o", linestyle="--", linewidth=1.8, label="Policy changepoint regression")
plt.plot(future_years, exp_recent_y, color="darkgreen", marker="o", linestyle="--", linewidth=1.8, label="Recent 5-year trend")

plt.axvline(2020, color="gray", linestyle=":", label="FY2020 COVID continuous enrollment")
plt.axvline(2023, color="darkorange", linestyle=":", label="FY2023 unwinding")
plt.axvline(2024, color="purple", linestyle=":", label="FY2024 later unwinding/taper")
plt.axvline(exp_years[-1], color="black", linestyle="-.", alpha=0.6, label="Forecast starts")

plt.title("National Medicaid + CHIP Expenditure Forecast: Annual Model Comparison")
plt.xlabel("Fiscal Year")
plt.ylabel("Total Computable Expenditures, Billions of Dollars")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(results_folder / "national_expenditure_model_comparison_annual.png", dpi=200)
plt.close()


# ------------------------------------------------
# 16. Draw expenditure policy changepoint model plot
# ------------------------------------------------

plt.figure(figsize=(13, 7))
plt.plot(exp_years, exp_history_y, color="royalblue", marker="o", linewidth=2.2, label="Historical")
plt.fill_between(future_years, exp_policy_lower_y, exp_policy_upper_y, color="lightcoral", alpha=0.25, label="95% range")
plt.plot(future_years, exp_policy_y, color="firebrick", marker="o", linestyle="--", linewidth=1.8, label="Policy changepoint forecast")

plt.axvline(2020, color="gray", linestyle=":", label="FY2020 COVID continuous enrollment")
plt.axvline(2023, color="darkorange", linestyle=":", label="FY2023 unwinding")
plt.axvline(2024, color="purple", linestyle=":", label="FY2024 later unwinding/taper")
plt.axvline(exp_years[-1], color="black", linestyle="-.", alpha=0.6, label="Forecast starts")

plt.title("National Medicaid + CHIP Expenditure Forecast: Policy Changepoint Model")
plt.xlabel("Fiscal Year")
plt.ylabel("Total Computable Expenditures, Billions of Dollars")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(results_folder / "national_expenditure_policy_changepoint_forecast.png", dpi=200)
plt.close()


# -------------------------
# 17. Save model notes
# -------------------------

notes = f"""Data scope: Medicaid + CHIP combined, 50 states and District of Columbia.
CHIP expenditure = MCHIP + MCHIP 20% + separate CHIP (including its reported administration).
Medicaid expenditure = MAP, excluding Medicaid ADM. These are reported net expenditures.
National Enrollment Model Comparison

Models included:
1. Holt damped trend
2. Policy changepoint regression
3. Recent 12-month trend

Enrollment data:
Monthly national Total Medicaid and CHIP Enrollment, {month_labels[0]} to {month_labels[-1]}
The national number is created by adding all state enrollment values together
for each reporting month.

Expenditure data:
Annual national Medicaid and CHIP Total Net Expenditures Total Computable, FY{exp_years[0]} to FY{exp_years[-1]}
The national number is created by adding all state expenditure values together
for each fiscal year.

Policy changepoint regression:
This model is inspired by Prophet's changepoint idea. It adds separate trend
terms after major Medicaid policy dates:
- 2020-03: COVID continuous enrollment begins
- 2023-04: Medicaid unwinding begins
- 2024-07: later unwinding/taper point

How the changepoint dates were chosen:
These dates were selected based on major Medicaid policy events. They were not
chosen randomly and were not automatically estimated by this simple model.

References:
- CMS fact sheet:
  https://www.cms.gov/newsroom/fact-sheets/cms-waivers-flexibilities-transition-forward-covid-19-public-health-emergency
- Medicaid.gov COVID-19 Public Health Emergency Flexibilities and Returning to
  Regular Operations:
  https://www.medicaid.gov/resources-for-states/coronavirus-disease-2019-covid-19
- CMS blog on Medicaid unwinding timeline:
  https://www.cms.gov/newsroom/blog/calling-partners-help-people-stay-covered

Policy model residual standard deviation:
Enrollment Holt damped trend = {round(holt_std):,}
Enrollment policy changepoint regression = {round(policy_std):,}
Enrollment recent 12-month trend = {round(recent_std):,}
Expenditure Holt damped trend = ${round(exp_holt_std):,}
Expenditure policy changepoint regression = ${round(exp_policy_std):,}
Expenditure recent 5-year trend = ${round(exp_recent_std):,}
"""

(results_folder / "national_model_comparison_notes.txt").write_text(notes)

print("Saved national forecast tables to Nationalized/tables")
print("Saved national forecast results to Nationalized/results")
