import requests
from pydantic import BaseModel
from typing import Dict, Union

class CurrencyInput(BaseModel):
    currency: Dict[str, float]

def get_usd_inr_rate() -> float:
    """Fetch USD to INR exchange rate from exchangerate-api.com"""
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url)
        data = response.json()
        return data['rates']['INR']
    except Exception as e:
        print(f"Error fetching USD/INR rate: {e}")
        return 83.5  # Fallback rate (approximate as of 2025)

def get_xdai_usd_price() -> float:
    """Fetch xDAI price in USD from CoinGecko"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=xdai&vs_currencies=usd"
        response = requests.get(url)
        data = response.json()
        return data['xdai']['usd']
    except Exception as e:
        print(f"Error fetching xDAI/USD price: {e}")
        return 1.0  # Fallback price (xDAI is ~1:1 with USD)

def convert_currency(amount: float, from_currency: str) -> Dict[str, Union[float, str]]:
    """Convert amount from from_currency to all currencies (USD, INR, xDAI)"""
    usd_inr = get_usd_inr_rate()
    xdai_usd = get_xdai_usd_price()

    # Convert input amount to USD first
    if from_currency == "USD":
        usd_amount = amount
    elif from_currency == "INR":
        usd_amount = amount / usd_inr
    elif from_currency == "xDAI":
        usd_amount = amount * xdai_usd
    else:
        return {"error": "Invalid from_currency"}

    # Convert USD to all target currencies
    result = {
        "USD": round(usd_amount, 4),
        "INR": round(usd_amount * usd_inr, 4),
        "xDAI": round(usd_amount / xdai_usd, 4)
    }
    return result

def process_currency_input(input_dict: Dict[str, float]) -> Dict[str, Union[float, str]]:
    """Process input dictionary and return conversions"""
    if len(input_dict) != 1:
        return {"error": "Input must contain exactly one currency and amount"}
    
    from_currency = list(input_dict.keys())[0]
    amount = input_dict[from_currency]
    
    if not isinstance(amount, (int, float)) or amount < 0:
        return {"error": "Amount must be a non-negative number"}
    
    return convert_currency(amount, from_currency)