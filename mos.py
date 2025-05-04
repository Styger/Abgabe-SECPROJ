import logging
from typing import Dict
from ten_cap import calculate_ten_cap_price
from fmp_api import get_valid_price
#from mos import mos_growth_estimate


def calculate_intrinsic_value(eps_now, growth_rate, breach_year, discount_rate=0.15, mos=0.50) -> Dict:
    """
    Calculates the intrinsic value and MOS price based on EPS and growth rate.
    
    Args:
        eps_now: Current earnings per share
        growth_rate: Expected growth rate (as decimal)
        breach_year: Year of calculation
        discount_rate: Discount rate for present value calculation (default: 0.15)
        mos: Margin of Safety percentage (default: 0.50)
    
    Returns:
        Dictionary containing calculated values including EPS projection, future value,
        fair value today, and MOS price
    """
    if eps_now <= 0 or growth_rate <= 0:
        logging.warning("Invalid EPS or growth rate. Returning 0 values.")
        return {
            'EPS_10y': 0,
            'Future Value': 0,
            'Fair Value Today': 0,
            'MOS Price (50%)': 0
        }

    eps_10y = eps_now * ((1 + growth_rate) ** 10)
    future_pe = growth_rate * 200  
    future_value = eps_10y * future_pe
    fair_value_today = future_value / ((1 + discount_rate) ** 10)
    mos_price = fair_value_today * (1 - mos)

    result = {
        'Groth_rate': round(growth_rate * 100, 2),
        'EPS_now': round(eps_now, 2),
        'EPS_10y': round(eps_10y, 2),
        'Future Value': round(future_value, 2),
        'Fair Value Today': round(fair_value_today, 2),
        'MOS Price (50%)': round(mos_price, 2)
    }

    logging.info("Intrinsic Value Result for year %s: %s", breach_year, result)
    return result 




if __name__ == "__main__":
    # calculate_intrinsic_value(eps_now, growth_rate, breach_year)
    calculate_intrinsic_value(0.5, 0.3, 2020) # you can take the groth_rate from groth_estimation.py, breach year is only for logging
