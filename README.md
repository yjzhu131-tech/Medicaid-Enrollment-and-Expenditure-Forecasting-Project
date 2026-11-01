# Medicaid Enrollment and Expenditure Forecasting

Analyze historical Medicaid and CHIP enrollment and spending, and forecast trends over the next 10 years.

The project covers **New York, Illinois, Washington, and Pennsylvania**, with additional national forecasts.

## Read the Article

[Medicaid and CHIP: Fewer Enrollees, Continued Spending Pressure](reports/medicaid-state-trends.html)

To read the formatted article with all charts, open the link above, click **Download raw file** on GitHub, and open the downloaded HTML file in your web browser. If you have downloaded or cloned this repository, double-click `reports/medicaid-state-trends.html` to open it directly. All charts are embedded in the file, so it can be read offline.

## What This Project Does

- Cleans monthly enrollment and annual expenditure data.
- Forecasts enrollment and spending using policy changepoint regression and Holt damped trend models.
- Calculates annual spending per average enrollee.
- Produces forecast tables, charts, and a summary report.

## Project Structure

| Directory | Contents |
| --- | --- |
| `data/` | Raw and cleaned datasets |
| `New_York/`, `Illinois/`, `Washington/`, `Pennsylvania/` | State analysis scripts, charts, and forecast tables |
| `reports/` | Summary report and report preparation scripts |

## Tools

Python, NumPy, Matplotlib, and Excel data processing libraries.

```bash
pip install -r requirements.txt
```

Forecasts extend historical patterns and policy assumptions; they are not official projections.
