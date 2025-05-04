import os
import pandas as pd
from fmp_api import get_year_data_by_range, get_price_on_date
from csv_report import append_mos_to_csv

# === Map of ticker to breach year ===
ticker_map = {
    "TMUS": 2021,
    "OKTA": 2022,
    "EFX": 2017,
    "CON.DE": 2022,
    "MPL.AX": 2022,
    "COF": 2019,
    "GRMN": 2020
}

# === Ensure output folder exists ===
output_folder = "./output"
os.makedirs(output_folder, exist_ok=True)


# === Process each company ===
for ticker, breach_year in ticker_map.items():
    # Start 6 years before the breach to cover MOS growth (pre-breach -1) and ensure enough EPS history
    start_year = breach_year - 6

    # Calculate number of years needed (breach year - start + 3 post-breach years)
    required_years = (breach_year - start_year) + 3 + 1  # = 10 total

    print(f"\nMetrics for {ticker} (start {start_year}, breach {breach_year}):\n" + "-" * 50)

    try:
        # Fetch financial data for the required range
        data, metrics_raw = get_year_data_by_range(ticker, start_year, years=required_years)
        df = pd.DataFrame(data)

        if len(df) < required_years:
            print(f"[WARNING] {ticker}: Only {len(df)} years of data returned, expected {required_years}. Results may be incomplete.")

        print(df)

        file_path = os.path.join(output_folder, f"{ticker}_metrics.csv")
        try:
            append_mos_to_csv(df, file_path, metrics_raw, breach_year, start_year, ticker)
        except Exception as e:
            print(f"[ERROR] Skipping MOS for {ticker}: {e}")
            df.to_csv(file_path, index=False)

    except Exception as e:
        print(f"[ERROR] Skipping {ticker}: {e}")


