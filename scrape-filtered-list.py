import pandas as pd
import re

def normalize(text):
    """Lowercase, remove spaces and hyphens."""
    if pd.isna(text):
        return ''
    return re.sub(r'[\s\-]', '', str(text).lower())

def load_protein_symbols(filepath):
    df = pd.read_excel(filepath)
    symbols = df.iloc[:, 0].dropna().astype(str)
    return [normalize(symbol) for symbol in symbols]

def match_symbol_in_name(name, symbols):
    """Check if any symbol is substring of the normalized name."""
    name_norm = normalize(name)
    return any(symbol in name_norm for symbol in symbols)

def filter_scrape_data(scrape_filepath, symbols):
    # Load all sheets
    sheets = pd.read_excel(scrape_filepath, sheet_name=None)
    filtered_sheets = {}

    for sheet_name, df in sheets.items():
        if df.shape[1] < 2:
            # Skip sheets with less than 2 columns
            filtered_sheets[sheet_name] = df
            continue

        # Column B (index 1) is the name column
        mask = df.iloc[:, 1].apply(lambda name: match_symbol_in_name(name, symbols))
        filtered_df = df[mask].copy()

        filtered_sheets[sheet_name] = filtered_df

    return filtered_sheets

def main():
    # File paths
    protein_list_file = 'protein-list.xlsx'
    scrape_data_file = 'scrape-data-protein.xlsx'
    output_file = 'filtered-scrape-protein-data.xlsx'

    # Process
    symbols = load_protein_symbols(protein_list_file)
    filtered_sheets = filter_scrape_data(scrape_data_file, symbols)

    # Save results
    with pd.ExcelWriter(output_file) as writer:
        for sheet_name, df in filtered_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f'Filtered data saved to {output_file}')

if __name__ == '__main__':
    main()
