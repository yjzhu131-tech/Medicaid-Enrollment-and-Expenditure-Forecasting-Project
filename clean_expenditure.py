import csv
from pathlib import Path

from openpyxl import load_workbook


raw_folder = Path("data/raw/expenditure")
clean_file = Path("data/clean/expenditure_clean_map_total.csv")

# This script creates one clean expenditure table from many raw Excel files.

# Used to add state abbreviations to the clean file.
state_abbr = {
    "Alabama": "AL",
    "Alaska": "AK",
    "American Samoa": "AS",
    "Amer. Samoa": "AS",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District of Columbia": "DC",
    "Dist. Of Col.": "DC",
    "Dist. of Col.": "DC",
    "Florida": "FL",
    "Georgia": "GA",
    "Guam": "GU",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Northern Mariana Islands": "MP",
    "N. Mariana Islands": "MP",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Puerto Rico": "PR",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virgin Islands": "VI",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}

name_fix = {
    "Amer. Samoa": "American Samoa",
    "Dist. Of Col.": "District of Columbia",
    "Dist. of Col.": "District of Columbia",
    "N. Mariana Islands": "Northern Mariana Islands",
}

# This list will store all cleaned rows before writing the final CSV.
clean_rows = []

# The old 1997-2001 file has one sheet per fiscal year.
# Inside each sheet, all states are stacked vertically.
old_file = raw_folder / "FMR1997through2001.xlsx"

if old_file.exists():
    # Open the 1997-2001 workbook.
    workbook = load_workbook(old_file, read_only=True, data_only=True)

    for sheet_name in workbook.sheetnames:
        # Sheet names look like FMR1997, FMR1998, etc.
        year = int(sheet_name.replace("FMR", ""))
        sheet = workbook[sheet_name]
        current_state = ""

        for row in sheet.iter_rows(values_only=True):
            first_cell = str(row[0]).strip() if row and row[0] is not None else ""

            # A state name marks the beginning of that state's block.
            if first_cell in state_abbr:
                current_state = first_cell
                continue

            # Skip the national total block because this clean file is state-level.
            if first_cell == "National Totals":
                current_state = ""
                continue

            # After a state name, this row contains the MAP total expenditure.
            if first_cell == "Total Net Expenditures" and current_state:
                state_name = name_fix.get(current_state, current_state)
                abbreviation = state_abbr[current_state]
                total_computable = int(round(row[1]))
                clean_rows.append([
                    state_name,
                    abbreviation,
                    year,
                    total_computable,
                ])
                current_state = ""

    workbook.close()


# The 2002-2011 file also has one sheet per fiscal year.
# Its layout is similar to the 1997-2001 file.
old_file = raw_folder / "NetExpenditure02through11.xlsx"

if old_file.exists():
    # Open the 2002-2011 workbook.
    workbook = load_workbook(old_file, read_only=True, data_only=True)

    for sheet_name in workbook.sheetnames:
        # Sheet names are just years, such as 2002, 2003, etc.
        year = int(sheet_name)
        sheet = workbook[sheet_name]
        current_state = ""

        for row in sheet.iter_rows(values_only=True):
            first_cell = str(row[0]).strip() if row and row[0] is not None else ""

            # A state name marks the beginning of that state's block.
            if first_cell in state_abbr:
                current_state = first_cell
                continue

            # Skip the national total block because this clean file is state-level.
            if first_cell == "National Totals":
                current_state = ""
                continue

            # After a state name, this row contains the MAP total expenditure.
            if first_cell == "Total Net Expenditures" and current_state:
                state_name = name_fix.get(current_state, current_state)
                abbreviation = state_abbr[current_state]
                total_computable = int(round(row[1]))
                clean_rows.append([
                    state_name,
                    abbreviation,
                    year,
                    total_computable,
                ])
                current_state = ""

    workbook.close()


# FY2012 has one sheet per state.
# The MAP Total Net Expenditures row is still in column A,
# and Total Computable is still in column B.
fy2012_file = raw_folder / "financial-management-report-fy2012-13" / "FMR Net Expenditures FY12.xlsx"

if fy2012_file.exists():
    # Open the FY2012 workbook.
    workbook = load_workbook(fy2012_file, read_only=True, data_only=True)

    for sheet_name in workbook.sheetnames:
        # Each sheet is one state, so sheet_name is the state name.
        if sheet_name == "National Totals":
            continue
        if sheet_name not in state_abbr:
            continue

        state_name = name_fix.get(sheet_name, sheet_name)
        abbreviation = state_abbr[sheet_name]
        sheet = workbook[sheet_name]

        for row in sheet.iter_rows(values_only=True):
            service_category = row[0]

            # For FY2012, this row gives the Medicaid MAP total.
            if service_category == "Total Net Expenditures":
                total_computable = int(round(row[1]))
                clean_rows.append([
                    state_name,
                    abbreviation,
                    2012,
                    total_computable,
                ])
                break

    workbook.close()


# FY2013-FY2024 use the newer format: one sheet for each program and state.
for file_path in sorted(raw_folder.glob("financial-management-report-fy*/*.xlsx")):
    file_name = file_path.name

    # Ignore temporary Excel files.
    # These files often appear when an Excel file is open.
    if file_name.startswith("~$"):
        continue

    # Use Medicaid FMR files only. Do not use CHIP files.
    if "CHIP" in file_name.upper():
        continue

    # FY2012 uses a different format and was already handled above.
    if file_name == "FMR Net Expenditures FY12.xlsx":
        continue

    # Get the year from the folder name, such as financial-management-report-fy2024.
    folder_name = file_path.parent.name
    if folder_name == "financial-management-report-fy2012-13":
        year = 2013
    else:
        year = int(folder_name[-4:])

    workbook = load_workbook(file_path, read_only=True, data_only=True)

    for sheet_name in workbook.sheetnames:
        # Use MAP sheets only, such as MAP - Pennsylvania.
        if not sheet_name.startswith("MAP - "):
            continue

        state_name = sheet_name.replace("MAP - ", "").strip()

        # Skip national total because it is not a state.
        if state_name == "National Totals":
            continue

        clean_state_name = name_fix.get(state_name, state_name)
        abbreviation = state_abbr[state_name]

        sheet = workbook[sheet_name]

        # Read the Excel sheet row by row.
        # In each row:
        # row[0] is column A, Service Category.
        # row[1] is column B, Total Computable.
        for row in sheet.iter_rows(values_only=True):
            service_category = row[0]

            # Find the row where column A says Total Net Expenditures.
            if service_category == "Total Net Expenditures":
                # Then take column B from that row.
                total_computable = int(round(row[1]))
                clean_rows.append([
                    clean_state_name,
                    abbreviation,
                    year,
                    total_computable,
                ])
                break

    workbook.close()

clean_rows.sort()

# CHIP-funded expenditure has three components. Older workbooks put these
# alongside Medicaid; FY2012 onward uses a separate CHIP workbook.
chip_components = {}
component_labels = {"C-Total Net": "MCHIP", "T-Total Net Expenditures": "MCHIP 20%", "Total": "CHIP"}

for filename in ("FMR1997through2001.xlsx", "NetExpenditure02through11.xlsx"):
    workbook = load_workbook(raw_folder / filename, read_only=True, data_only=True)
    for sheet in workbook:
        year = int(sheet.title.replace("FMR", ""))
        current_state = None
        for row in sheet.iter_rows(values_only=True):
            first = str(row[0]).strip() if row[0] is not None else ""
            if any(str(value).startswith("GUAM    Guam") for value in row):
                current_state = "GU"
            elif first in state_abbr:
                current_state = state_abbr[first]
            elif first and all(value in (None, "", " ") for value in row[1:]):
                current_state = None
            if current_state:
                for column, value in enumerate(row[:-1]):
                    label = str(value).strip()
                    if label in component_labels:
                        key = (current_state, year)
                        component = component_labels[label]
                        components = chip_components.setdefault(key, {})
                        if component in components:
                            raise ValueError(f"Duplicate CHIP total: {key}, {component}")
                        components[component] = int(round(row[column + 1]))
    workbook.close()

for file_path in sorted(raw_folder.glob("financial-management-report-fy*/*")):
    if "CHIP" not in file_path.name.upper() or file_path.name.startswith("~$"):
        continue
    if file_path.suffix not in (".xls", ".xlsx"):
        continue
    if file_path.parent.name.endswith("2012-13"):
        year = 2012 if "12" in file_path.stem else 2013
    else:
        year = int(file_path.parent.name[-4:])
    if file_path.suffix == ".xls":
        import xlrd
        workbook = xlrd.open_workbook(file_path)
        sheets = [(sheet.name, [sheet.row_values(i) for i in range(sheet.nrows)]) for sheet in workbook.sheets()]
    else:
        workbook = load_workbook(file_path, read_only=True, data_only=True)
        sheets = [(sheet.title, sheet.iter_rows(values_only=True)) for sheet in workbook]
    for sheet_name, rows in sheets:
        component, state = sheet_name.split(" - ", 1)
        if state == "National Totals":
            continue
        if component not in ("MCHIP", "MCHIP 20%", "CHIP"):
            raise ValueError(f"Unknown CHIP component: {sheet_name}")
        totals = [int(round(row[1])) for row in rows if str(row[0]).strip() in component_labels]
        if len(totals) != 1:
            raise ValueError(f"Expected one total: {file_path}, {sheet_name}")
        key = (state_abbr[state.strip()], year)
        components = chip_components.setdefault(key, {})
        if component in components:
            raise ValueError(f"Duplicate CHIP component: {key}, {component}")
        components[component] = totals[0]
    if file_path.suffix == ".xlsx":
        workbook.close()

combined_rows = []
for state, abbreviation, year, medicaid in clean_rows:
    components = chip_components.get((abbreviation, year), {})
    # T- qualifying-state expenditure did not appear in every older year.
    if not {"MCHIP", "CHIP"}.issubset(components):
        raise ValueError(f"Missing CHIP data: {abbreviation}, FY{year}")
    chip = sum(components.values())
    combined_rows.append([state, abbreviation, year, medicaid,
                          components["MCHIP"], components.get("MCHIP 20%", 0),
                          components["CHIP"], chip, medicaid + chip])

combined_file = clean_file.parent / "expenditure_clean_medicaid_chip_total.csv"
combined_file.parent.mkdir(parents=True, exist_ok=True)
with combined_file.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["State Name", "State Abbreviation", "Year",
                     "MAP Total Net Expenditures Total Computable",
                     "MCHIP Total Computable", "MCHIP 20% Total Computable",
                     "Separate CHIP Total Computable", "CHIP Total Net Expenditures Total Computable",
                     "Medicaid and CHIP Total Net Expenditures Total Computable"])
    writer.writerows(combined_rows)
print(f"Saved {len(combined_rows)} combined rows to {combined_file}")

# Make sure the clean folder exists before saving the CSV.
clean_file.parent.mkdir(parents=True, exist_ok=True)

# Save the final clean expenditure table.
with clean_file.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "State Name",
        "State Abbreviation",
        "Year",
        "MAP Total Net Expenditures Total Computable",
    ])
    writer.writerows(clean_rows)

print(f"Saved {len(clean_rows)} rows to {clean_file}")
