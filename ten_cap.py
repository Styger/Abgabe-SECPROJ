from fmp_api import (
    get_income_statement,
    get_cashflow_statement,
    get_key_metrics,
    get_year_data_by_range
)
import logging
from typing import Optional

# Configure logging to show debug messages in console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s'
)

def calculate_owner_earnings(profit_before_tax: float,
                           depreciation: float,
                           working_capital_change: float,
                           maintenance_capex: float) -> float:
    """
    Calculates Owner Earnings based on input values.
    All values should be in the same unit (millions).
    Working Capital Changes from Cash Flow Statement already have correct signs:
    - Increase in Receivables: negative (cash tied up)
    - Increase in Payables: positive (more financing)
    """
    # Check for zero values and log warnings
    if depreciation == 0:
        logging.warning("Depreciation is 0 - this is unusual and might indicate missing data")
    
    if working_capital_change == 0:
        logging.warning("Working Capital change is 0 - this is unusual and might indicate missing data")
    
    # Only 50% of Maintenance/CapEx is considered
    adjusted_maintenance = maintenance_capex * 0.5
    if adjusted_maintenance == 0:
        logging.warning("Maintenance CapEx is 0 - this is unusual and might indicate missing data")
    
    owner_earnings = (profit_before_tax 
                     + depreciation 
                     + working_capital_change  # Already contains all Working Capital changes with correct signs
                     - adjusted_maintenance)
    
    return owner_earnings

def get_ten_cap_data(ticker: str, year: int = None):
    """
    Holt die notwendigen Daten für die TEN CAP Analyse und berechnet den TEN CAP Buy Price
    """
    try:
        # Berechne den TEN CAP Price
        ten_cap_price = calculate_ten_cap_price(ticker, year)
        
        if ten_cap_price is None:
            return None
            
        return ten_cap_price

    except Exception as e:
        logging.error(f"Fehler bei der TEN CAP Analyse für {ticker}: {e}")
        return None

def print_ten_cap_analysis(ticker: str):
    """
    Führt die TEN CAP Analyse durch und gibt die Ergebnisse formatiert aus
    """
    results = get_ten_cap_data(ticker)
    
    if results:
        print(f"\nTEN CAP Analyse für {ticker} ({results['year']})")
        print("-" * 50)
        print(f"Gewinn vor Steuern:      ${results['profit_before_tax']:,.2f}M")
        print(f"+ Abschreibungen:        ${results['depreciation']:,.2f}M")
        print(f"{'+ ' if results['working_capital_change'] >= 0 else '- '}Δ Working Capital:     ${abs(results['working_capital_change']):,.2f}M")
        print(f"- 50% Maintenance CapEx: ${results['maintenance_capex']*0.5:,.2f}M")
        print("-" * 50)
        print(f"= Owner Earnings:        ${results['owner_earnings']:,.2f}M")
        print(f"Aktien (Mio):           {results['shares_outstanding']:,.2f}")
        print(f"Earnings per Share:      ${results['earnings_per_share']:,.2f}")
        print("=" * 50)
        print(f"TEN CAP Buy Price:       ${results['ten_cap_buy_price']:,.2f}")
    else:
        print(f"Konnte keine TEN CAP Analyse für {ticker} durchführen")

def calculate_working_capital_change(cashflow_data: dict) -> tuple:
    """
    Calculates the change in working capital from its components.
    All values from Cash Flow Statement already have correct signs:
    - Increase in Assets (Receivables): negative (cash tied up)
    - Increase in Liabilities (Payables): positive (more financing)
    
    Returns:
        tuple: (working_capital_change, components_dict)
    """
    MILLION = 1_000_000
    
    # Assets (negative when increasing)
    accounts_receivable_change = cashflow_data.get('accountsReceivables', 0) / MILLION
    
    # Liabilities (positive when increasing)
    accounts_payable_change = cashflow_data.get('accountsPayables', 0) / MILLION
    
    # Total Working Capital Change
    working_capital_change = (
        accounts_receivable_change +  # Accounts Receivable
        accounts_payable_change      # Accounts Payable
    )
    
    components = {
        'accounts_receivable': accounts_receivable_change,
        'accounts_payable': accounts_payable_change
    }
    
    return working_capital_change, components

def calculate_ten_cap_price(ticker: str, year: int = None) -> Optional[float]:
    """
    Calculate the TEN CAP buy price for a given stock.
    
    Args:
        ticker: Stock symbol
        year: The year for which to calculate the TEN CAP price
        
    Returns:
        float: TEN CAP buy price or None if calculation fails
    """
    try:
        # Get financial data
        income_data = get_income_statement(ticker, limit=10)
        cashflow_data = get_cashflow_statement(ticker, limit=10)
        metrics = get_key_metrics(ticker, limit=10)

        if not income_data or not cashflow_data or not metrics:
            logging.error(f"Could not get financial data for {ticker}")
            return None

        year_str = str(year)
        logging.info(f"\nProcessing year {year}")

        # Find data for the specified year
        current_year_data = next((data for data in income_data if str(data.get('calendarYear')) == year_str), None)
        current_cashflow = next((data for data in cashflow_data if str(data.get('calendarYear')) == year_str), None)
        current_metrics = next((data for data in metrics if str(data.get('calendarYear')) == year_str), None)

        if not current_year_data or not current_cashflow or not current_metrics:
            logging.error(f"Could not find complete data for {year}")
            return None

        # Convert to millions
        MILLION = 1_000_000

        # Extract required values
        profit_before_tax = current_year_data.get('incomeBeforeTax', 0) / MILLION
        
        # Try different depreciation fields
        depreciation = (
            current_cashflow.get('depreciationAndAmortization', 0) or
            current_cashflow.get('depreciation', 0) or
            current_cashflow.get('depreciationAmortizationDepletion', 0) or
            current_cashflow.get('depreciationDepletionAndAmortization', 0)
        ) / MILLION

        if depreciation == 0:
            logging.warning(f"Could not find any depreciation values for {ticker} in {year}")
            logging.debug("Available depreciation fields:")
            for key, value in current_cashflow.items():
                if 'depreciation' in key.lower():
                    logging.debug(f"{key}: ${value/MILLION:.2f}M")
        
        # Berechne Working Capital Änderungen
        working_capital_change, wc_components = calculate_working_capital_change(current_cashflow)
        
        maintenance_capex = abs(current_cashflow.get('capitalExpenditure', 0)) / MILLION

        # Try different ways to get shares outstanding
        shares_outstanding = (
            current_metrics.get('weightedAverageShsOut', 0) or
            current_metrics.get('weightedAverageShsOutDil', 0) or
            current_year_data.get('weightedAverageShsOut', 0) or
            current_year_data.get('weightedAverageShsOutDil', 0)
        ) / MILLION

        if shares_outstanding <= 0:
            logging.error(f"No valid shares outstanding found for {ticker}")
            return None

        # Print analysis
        logging.info(f"\nTEN CAP Analysis for {ticker} - {year}:")
        logging.info("-" * 50)
        
        # Print Working Capital components
        logging.info("\nWorking Capital Components:")
        logging.info(f"Δ Accounts Receivable:      ${wc_components['accounts_receivable']:,.2f}M")
        logging.info(f"Δ Accounts Payable:         ${wc_components['accounts_payable']:,.2f}M")
        logging.info(f"= Δ Working Capital Total:  ${working_capital_change:,.2f}M")
        logging.info("-" * 50)

        # Print main analysis
        logging.info(f"Income Before Tax:       ${profit_before_tax:,.2f}M")
        logging.info(f"+ Depreciation:          ${depreciation:,.2f}M")
        logging.info(f"Δ Working Capital:       ${working_capital_change:,.2f}M")
        logging.info(f"  Δ Accounts Receivable:        ${wc_components['accounts_receivable']:,.2f}M")
        logging.info(f"  Δ Accounts Payable:           ${wc_components['accounts_payable']:,.2f}M")
        logging.info(f"- 50% Maintenance CapEx: ${maintenance_capex*0.5:,.2f}M")
        logging.info("-" * 50)

        # Calculate owner earnings using total working capital change
        owner_earnings = calculate_owner_earnings(
            profit_before_tax,
            depreciation,
            working_capital_change,
            maintenance_capex
        )

        # Calculate earnings per share
        eps = owner_earnings / shares_outstanding if shares_outstanding > 0 else 0

        # Calculate TEN CAP buy price (10% capitalization rate)
        ten_cap_price = eps / 0.10

        # Print results
        logging.info(f"= Owner Earnings:        ${owner_earnings:,.2f}M")
        logging.info(f"Aktien (Mio):           {shares_outstanding:,.2f}")
        logging.info(f"Earnings per Share:      ${eps:,.2f}")
        logging.info("=" * 50)
        logging.info(f"TEN CAP Buy Price:       ${ten_cap_price:,.2f}")
        logging.info("=" * 50)

        # Debug: Print all cashflow fields
        logging.debug(f"\nAll Cash Flow Fields for {year_str}:")
        for key, value in current_cashflow.items():
            if isinstance(value, (int, float)):
                logging.debug(f"{key}: ${value/MILLION:.2f}M")
        logging.debug("-" * 50)

        return ten_cap_price

    except Exception as e:
        logging.error(f"Error in TEN CAP analysis for {ticker}: {e}")
        return None

if __name__ == "__main__":
    # Test mit mehreren Jahren
    ticker = "COF"
    test_years = [2018, 2019, 2020, 2021, 2022]
    
    logging.info("\nTEN CAP Analysis for Multiple Years:\n")
    for year in test_years:
        price = calculate_ten_cap_price(ticker, year)
        logging.info(f"{year}: ${price:.2f}" if price is not None else f"{year}: N/A") 