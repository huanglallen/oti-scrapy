import pandas as pd
from openpyxl import load_workbook

# Load your CSV file (replace file name with the appropriate one)
df = pd.read_csv('abcam.csv')

# Save to Excel
excel_path = 'output.xlsx'
df.to_excel(excel_path, index=False)

# Adjust column widths
wb = load_workbook(excel_path)
ws = wb.active

for col in ws.columns:
    max_length = 0
    column_letter = col[0].column_letter
    for cell in col:
        if cell.value:
            max_length = max(max_length, len(str(cell.value)))
    ws.column_dimensions[column_letter].width = max_length + 2  # padding

print("output file created!")
wb.save(excel_path)
