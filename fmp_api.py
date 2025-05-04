from api_key import FMP_API_KEY
import requests
from log_config import setup_logging
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta


# Logging activation 
setup_logging()

# Hides INFO/DEBUG-Spam in Console
#setup_logging(console_level=logging.WARNING)

#Debug Logs in Console
#setup_logging(console_level=logging.DEBUG)

# seperate File for Logging
#setup_logging(log_filename="fmp_ap.log")

def get_income_statement(ticker, limit=20):
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?limit={limit}&apikey={FMP_API_KEY}"
    return requests.get(url).json()

def get_cashflow_statement(ticker, limit=20):
    url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?limit={limit}&apikey={FMP_API_KEY}"
    return requests.get(url).json()

def get_key_metrics(ticker, limit=20):
    url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?limit={limit}&apikey={FMP_API_KEY}"
    return requests.get(url).json()

def get_year_data_by_range(ticker, start_year, years=4):
    """
    Returns key financial metrics for a given ticker over a range of years,
    along with raw per-share values for MOS analysis.
    """
    income = get_income_statement(ticker)
    cashflow = get_cashflow_statement(ticker)
    metrics = get_key_metrics(ticker)

    def get_by_year(data, year):
        for entry in data:
            if str(entry.get("calendarYear")) == str(year):
                return entry
        return {}

    results = []
    book_list, eps_list, revenue_list, cashflow_list = [], [], [], []

    for year in range(start_year, start_year + years + 1):  # +1 to get full range
        i = get_by_year(income, year)
        c = get_by_year(cashflow, year)
        m = get_by_year(metrics, year)

        revenue = i.get('revenue', 0) / 1_000_000
        fcf = c.get('freeCashFlow', 0) / 1_000_000
        eps = i.get('eps', 0)
        roic = m.get('roic', None)

        # Append to results
        results.append({
            'Year': year,
            'Revenue (Mio)': round(revenue, 2),
            'Free Cash Flow (Mio)': round(fcf, 2),
            'EPS': round(eps, 2),
            'ROIC': f"{round(roic * 100, 2)} %" if roic is not None else "–"
        })

        # Collect values for MOS analysis
        book_list.append(m.get("bookValuePerShare", 0))
        eps_list.append(i.get("eps", 0))
        revenue_list.append(m.get("revenuePerShare", 0))
        cashflow_list.append(m.get("operatingCashFlowPerShare", 0))

    mos_metrics = {
        "book": book_list,
        "eps": eps_list,
        "revenue": revenue_list,
        "cashflow": cashflow_list
    }

    return results, mos_metrics

        


def get_price_on_date(ticker, date):
    logging.debug(f"Requesting stock price for {ticker} on {date}")
    try:
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={date}&to={date}&apikey={FMP_API_KEY}"
        response = requests.get(url)
        data = response.json()

        if "historical" in data and data["historical"]:
            price = data["historical"][0]["close"]
            logging.debug(f"Price found: {price}")
            return price
        else:
            logging.debug(f"No price found for {ticker} on {date}")
            return None

    except Exception as e:
        logging.error(f"Error fetching price for {ticker} on {date}: {e}")
        return None

def get_valid_price(ticker: str, base_date_str: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Versucht bis zu 14 Tage rückwärts einen gueltigen Aktienkurs zu finden.
    
    Args:
        ticker: Aktien-Symbol
        base_date_str: Ausgangsdatum im Format 'YYYY-MM-DD'
    
    Returns:
        Tuple von (Preis, Datum) oder (None, None) wenn kein Preis gefunden wurde
    """
    base_date = datetime.strptime(base_date_str, "%Y-%m-%d")
    for i in range(14):
        current_date = base_date - timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        price = get_price_on_date(ticker, date_str)
        logging.debug(f"Trying {ticker} on {date_str}: {price}")
        if price:
            return price, date_str

    logging.warning(f"No valid stock price found for {ticker} from {base_date_str} within 14 days")
    return None, None
