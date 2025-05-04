import pandas as pd
import logging
from typing import Dict, List
from growth_estimation import mos_growth_estimate
from mos import calculate_intrinsic_value
from fmp_api import get_valid_price
from ten_cap import calculate_ten_cap_price


def append_mos_to_csv(df: pd.DataFrame, 
                     filepath: str, 
                     metrics_raw: Dict[str, List[float]], 
                     breach_year: int, 
                     start_year: int, 
                     ticker: str) -> pd.DataFrame:
    """
    Generates a comprehensive MOS analysis report and appends it to an existing CSV file.
    
    Args:
        df: Input DataFrame with existing data
        filepath: Path to save the CSV report
        metrics_raw: Dictionary containing financial metrics data
        breach_year: Year of the breach event
        start_year: First year in the dataset
        ticker: Stock symbol
    
    Returns:
        DataFrame containing the original data plus the MOS analysis
    """
    logging.info(f"append_mos_to_csv → {filepath}")
    min_eps_years = (breach_year - start_year) + 4
    if len(metrics_raw.get("eps", [])) < min_eps_years:
        logging.warning(
            f"EPS data too short: Need {min_eps_years} years (from {start_year} to {breach_year + 3}), "
            f"but only have {len(metrics_raw.get('eps', []))} years"
        )

    # Step 1: Estimate growth based on metrics (from 5 years before the breach)
    details = mos_growth_estimate(metrics_raw, target_year=breach_year, data_start_year=start_year)

    # Step 2: Determine EPS at the time of the breach
    eps_values = metrics_raw.get("eps", [])
    eps_now = eps_values[breach_year - start_year] if len(eps_values) > (breach_year - start_year) else eps_values[-1] if eps_values else 0

    # Step 3: Get average growth rate (convert from percent to decimal)
    growth_rate = details.get("avg", 0) / 100 

    # Step 4: Calculate historical intrinsic values (from -1 to +3 years around breach)
    eps_list = metrics_raw.get("eps", [])
    fair_value_history = []

    for offset in range(-1, 4):  # -1 to +3
        year_index = breach_year - start_year + offset
        if 0 <= year_index < len(eps_list):
            eps = eps_list[year_index]
            year = start_year + year_index

            # Calculate dynamic growth rate for each year
            try:
                growth_details = mos_growth_estimate(
                    data_dict=metrics_raw,
                    target_year=year,
                    data_start_year=start_year
                )
                growth_rate = growth_details.get("avg", 0) / 100 
            except Exception as e:
                logging.warning(f"Growth calc failed for year {year}: {e}")
                growth_rate = 0

            # Get historical stock price
            base_date = f"{year}-12-31"
            stock_price, actual_date = get_valid_price(ticker, base_date)

            # Calculate TEN CAP price
            ten_cap_price = calculate_ten_cap_price(ticker, year)
            ten_cap_str = f"{ten_cap_price:.2f}" if ten_cap_price is not None else "N/A"

            # Calculate intrinsic value with year-specific growth rate
            intrinsic = calculate_intrinsic_value(
                eps_now=eps,
                growth_rate=growth_rate,
                breach_year=year,
                discount_rate=0.15,
                mos=0.50
            )

            fair_value_history.append({
                "Year": year,
                "EPS": round(eps, 2),
                "EPS in 10 Years": intrinsic['EPS_10y'],
                "Future Value": intrinsic['Future Value'],
                "Fair Value MOS": intrinsic['Fair Value Today'],
                "MOS Price (50%)": intrinsic['MOS Price (50%)'],
                "TEN CAP Buy Price": ten_cap_str,
                "Fair Value TEN CAP": f"{float(ten_cap_price) * 2:.2f}" if ten_cap_price is not None else "N/A",
                "Growth Rate (%)": growth_details.get("avg", "N/A"),
                "Stock Price (12-31)": round(stock_price, 2) if stock_price else "N/A",
                "Price Date Used": actual_date if actual_date else "N/A"
            })

    # Step 5: Prepare MOS summary rows for CSV
    spacer = pd.DataFrame([[""] * len(df.columns)], columns=df.columns)
    mos_summary = pd.DataFrame([
        {df.columns[0]: "Book CAGR (avg)", df.columns[1]: f"{details.get('book', 0.0)} %"},
        {df.columns[0]: "EPS CAGR (avg)", df.columns[1]: f"{details.get('eps', 0.0)} %"},
        {df.columns[0]: "Revenue/Share CAGR (avg)", df.columns[1]: f"{details.get('revenue', 0.0)} %"},
        {df.columns[0]: "Cashflow/Share CAGR (avg)", df.columns[1]: f"{details.get('cashflow', 0.0)} %"},
        {df.columns[0]: "Avg Growth Rate", df.columns[1]: f"{details.get('avg', 0.0)} %"},
        {df.columns[0]: "EPS in 10 Years", df.columns[1]: f"{intrinsic['EPS_10y']}"},
        {df.columns[0]: "Future Value", df.columns[1]: f"{intrinsic['Future Value']}"},
        {df.columns[0]: "Fair Value MOS", df.columns[1]: f"{intrinsic['Fair Value Today']}"},
        {df.columns[0]: "MOS Price (50%)", df.columns[1]: f"{intrinsic['MOS Price (50%)']}"},
        {df.columns[0]: "TEN CAP Buy Price", df.columns[1]: ten_cap_str},
        {df.columns[0]: "Fair Value TEN CAP", df.columns[1]: f"{float(ten_cap_price) * 2:.2f}" if ten_cap_price is not None else "N/A"}
    ])

    # Convert fair value history to DataFrame
    fair_df = pd.DataFrame(fair_value_history)
    fair_df = fair_df.rename(columns={"Year": df.columns[0]})

    # Step 6: Combine all components and save
    result_df = pd.concat([df, spacer, mos_summary, spacer, fair_df], ignore_index=True)
    result_df.to_csv(filepath, index=False)

    # Step 7: Log results
    logging.info(f"Saved results to {filepath}")
    logging.info("Fair Value history:")
    for row in fair_value_history:
        logging.info(row)

    return result_df 