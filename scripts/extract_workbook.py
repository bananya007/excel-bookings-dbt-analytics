from pathlib import Path

import pandas as pd


workbook = Path("legacy/regional_bookings_report_FINAL_v7_corrected.xlsx")
output_folder = Path("seeds")

sheets = {
    "Raw_Bookings": (1, "raw_bookings.csv", 9),
    "Rates": (0, "raw_rates.csv", 4),
    "Rep_Targets": (0, "raw_rep_targets.csv", 4),
    "Rep_Master": (0, "rep_master.csv", 4),
}

output_folder.mkdir(exist_ok=True)

for sheet_name, (header_row, output_name, column_count) in sheets.items():
    data = pd.read_excel(
        workbook,
        sheet_name=sheet_name,
        header=header_row,
    )
    
    data = data.iloc[:, :column_count]

    data = data.dropna(axis=0, how="all")
    data = data.dropna(axis=1, how="all")

    data.to_csv(output_folder / output_name, index=False)

    print(f"Extracted {sheet_name} → {output_name}")