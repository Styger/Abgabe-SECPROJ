import logging
from typing import Dict, List
from fmp_api import get_year_data_by_range, get_price_on_date
import pandas as pd

def calculate_cagr(start, end, years):
    """
    Calculates the Compound Annual Growth Rate (CAGR) between two values over a specified time period.
    
    CAGR = (End Value / Start Value)^(1/years) - 1
    
    Args:
        start (float): Initial value
        end (float): Final value
        years (float): Number of years between start and end value
    
    Returns:
        float: CAGR as a decimal (e.g., 0.15 for 15% growth)
               Returns 0 if input values are invalid (negative, zero, or non-numeric)
    """
    logging.debug(f"calculate_cagr(start={start}, end={end}, years={years})")
    try:
        start = float(start)
        end = float(end)
        years = float(years)
    except Exception as e:
        logging.warning(f"Conversion failed: {e}")
        return 0

    if start <= 0 or end <= 0 or years <= 0:
        logging.warning("Invalid input for CAGR calculation. Returning 0.")
        return 0

    return (end / start) ** (1 / years) - 1


def mos_growth_estimate(data_dict: Dict[str, List[float]], target_year: int, data_start_year: int) -> Dict[str, float]:
    """
    Calculates growth estimates for Margin of Safety (MOS) analysis based on multiple financial metrics.
    Analyzes 5-year segments before the target year for each metric (EPS, Revenue, Book Value, Cashflow).
    
    The function:
    1. Takes a 6-year window before target_year
    2. Calculates single CAGR over the entire 5-year period
    3. Handles negative/invalid values by assigning 0% growth
    4. Averages the growth rates for each metric
    5. Calculates an overall average growth rate
    
    Args:
        data_dict (Dict[str, List[float]]): Dictionary with lists of values for each metric
            Keys: 'eps', 'revenue', 'book', 'cashflow'
        target_year (int): Year for which to calculate growth estimates
        data_start_year (int): First year in the dataset
    
    Returns:
        Dict[str, float]: Dictionary with CAGR results for each metric and overall average
            Keys: 'eps', 'revenue', 'book', 'cashflow', 'avg'
            Values: Growth rates as percentages (e.g., 15.0 for 15%)
    
    Raises:
        ValueError: If insufficient data points are available before target year
    """
    logging.debug(f"Called mos_growth_estimate (target_year={target_year}, start={data_start_year})")

    start_index = target_year - data_start_year - 5
    if start_index < 0:
        raise ValueError("Not enough data points before target year to calculate CAGR")

    details = {}
    growths = []

    for key, values in data_dict.items():
        logging.debug(f"Metric: {key} → values: {values}")

        if len(values) < start_index + 6:
            logging.warning(f"Not enough data for metric '{key}'. Skipping.")
            details[key] = 0
            continue

        sub_values = values[start_index:start_index + 6]
        logging.debug(f"Subset for CAGR: {sub_values}")

        start = sub_values[0]
        end = sub_values[5]

        if start > 0 and end > 0:
            cagr = calculate_cagr(start, end, 5)
            growths.append(cagr)
            details[key] = round(cagr * 100, 2)
            logging.info(f"{key}: CAGR over 5y = {round(cagr * 100, 2)} %")
        else:
            logging.info(f"{key}: Invalid start or end value → CAGR set to 0")
            details[key] = 0
            growths.append(0)

    avg_growth = sum(growths) / len(growths) if growths else 0
    details['avg'] = round(avg_growth * 100, 2)
    logging.info(f"{'avg'}: average growth = {round(avg_growth* 100, 2)} %")

    # Log warning if the average growth across metrics is negative
    if avg_growth < 0:
        logging.warning(f"Company shows negative average growth: {details['avg']} %")

    logging.info(f"MOS Growth Summary: {details}")
    return details


if __name__ == "__main__":
    ticker_map = {
        #"TMUS": 2021#,
        #"OKTA": 2022#,
        #"EFX": 2017,
        #"CON.DE": 2022
        #"MPL.AX": 2022
        "COF": 2019#,
        #"GRMN": 2020
    }
    for ticker, breach_year in ticker_map.items():
        # Start 6 years before the breach to cover MOS growth (pre-breach -1) and ensure enough EPS history
        start_year = breach_year - 6

        # Calculate number of years needed (breach year - start + 3 post-breach years)
        required_years = (breach_year - start_year) + 3 + 1  

        data, mos_input = get_year_data_by_range(ticker, start_year, years=required_years)
        df = pd.DataFrame(data)

        if len(df) < required_years:
            print(f"[WARNING] {ticker}: Only {len(df)} years of data returned, expected {required_years}. Results may be incomplete.")

        print(df)
        mos_growth_estimate(data_dict=mos_input, target_year=breach_year, data_start_year=start_year)