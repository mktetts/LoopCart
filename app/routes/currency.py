from fastapi import APIRouter, HTTPException
from controllers.currency import process_currency_input, CurrencyInput
from typing import Dict, Union

router = APIRouter()

@router.post("/api/currency-conversion", response_model=Dict[str, Union[float, str]])
async def convert_currency(input_data: CurrencyInput):
    """Convert input currency to USD, INR, and xDAI"""
    result = process_currency_input(input_data.currency)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result