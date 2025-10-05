"""
Bank lookup utility based on routing numbers
This module provides functionality to identify banks by their routing numbers
"""

# Common US bank routing number prefixes and their corresponding banks
BANK_ROUTING_DATABASE = {
    # Major Banks
    "021000021": "Chase Bank",
    "021000322": "Chase Bank", 
    "022000020": "Chase Bank",
    "125000024": "Wells Fargo Bank",
    "121000248": "Wells Fargo Bank",
    "111000025": "Bank of America",
    "026009593": "Bank of America",
    "121042882": "Wells Fargo Bank",
    "053000196": "Bank of America",
    "054001204": "Bank of America",
    "063100277": "JPMorgan Chase Bank",
    "267084131": "JPMorgan Chase Bank",
    "021200025": "JPMorgan Chase Bank",
    
    # Regional Banks
    "122105278": "Wells Fargo Bank",
    "114000093": "PNC Bank",
    "043000096": "PNC Bank",
    "054000030": "Citizens Bank",
    "211274450": "TD Bank",
    "031201360": "TD Bank",
    "031100209": "TD Bank",
    "101000019": "Bank of the West",
    "321270742": "Huntington National Bank",
    "044000024": "Huntington National Bank",
    
    # Credit Unions and Others
    "307070115": "Navy Federal Credit Union",
    "256074974": "Navy Federal Credit Union",
    "211391825": "USAA Federal Savings Bank",
    "314074269": "Pentagon Federal Credit Union",
    "253177832": "Pentagon Federal Credit Union",
    "263179817": "Publix Employees Federal Credit Union (PEFCU)",
    "322271627": "Regions Bank",
    "062000019": "Regions Bank",
    "065400137": "KeyBank",
    "041001039": "KeyBank",
    
    # Online Banks
    "031176110": "Ally Bank",
    "124303120": "Capital One Bank",
    "051405515": "Capital One Bank",
    "103100195": "ING Direct (Capital One 360)",
    "031100649": "Discover Bank",
    "011103093": "American Express Bank",
}

# Bank routing number ranges (first 4 digits indicate Federal Reserve routing regions)
ROUTING_REGIONS = {
    "0210": "Boston, MA",
    "0211": "Boston, MA", 
    "0212": "New York, NY",
    "0213": "New York, NY",
    "0214": "Philadelphia, PA",
    "0215": "Philadelphia, PA",
    "0216": "Cleveland, OH",
    "0217": "Cleveland, OH",
    "0218": "Richmond, VA",
    "0219": "Richmond, VA",
    "0220": "Atlanta, GA",
    "0221": "Atlanta, GA",
    "0222": "Chicago, IL",
    "0223": "Chicago, IL",
    "0224": "St. Louis, MO",
    "0225": "St. Louis, MO",
    "0226": "Minneapolis, MN",
    "0227": "Minneapolis, MN",
    "0228": "Kansas City, MO",
    "0229": "Kansas City, MO",
    "0230": "Dallas, TX",
    "0231": "Dallas, TX",
    "0232": "San Francisco, CA",
    "0233": "San Francisco, CA",
}

def validate_routing_number(routing_number):
    """
    Validate routing number using the checksum algorithm
    """
    if not routing_number or len(routing_number) != 9:
        return False
    
    if not routing_number.isdigit():
        return False
    
    # Calculate checksum using the ABA routing number algorithm
    coefficients = [3, 7, 1, 3, 7, 1, 3, 7, 1]
    total = sum(int(digit) * coeff for digit, coeff in zip(routing_number, coefficients))
    
    return total % 10 == 0

def lookup_bank_by_routing(routing_number):
    """
    Lookup bank information by routing number
    """
    if not routing_number:
        return None
    
    # Clean the routing number
    routing_number = routing_number.replace("-", "").replace(" ", "")
    
    # Validate routing number
    if not validate_routing_number(routing_number):
        return {
            "valid": False,
            "error": "Invalid routing number format or checksum"
        }
    
    # Direct lookup
    bank_name = BANK_ROUTING_DATABASE.get(routing_number)
    
    if bank_name:
        region = ROUTING_REGIONS.get(routing_number[:4], "Unknown Region")
        return {
            "valid": True,
            "bank_name": bank_name,
            "routing_number": routing_number,
            "region": region,
            "source": "direct_match"
        }
    
    # Try to identify by region if direct match not found
    region_code = routing_number[:4]
    region = ROUTING_REGIONS.get(region_code, "Unknown Region")
    
    # Check for common bank patterns
    bank_guess = None
    if routing_number.startswith(("021", "267", "063")):
        bank_guess = "Chase Bank (likely)"
    elif routing_number.startswith(("121", "125")):
        bank_guess = "Wells Fargo Bank (likely)"
    elif routing_number.startswith(("111", "026", "053", "054")):
        bank_guess = "Bank of America (likely)"
    elif routing_number.startswith(("114", "043")):
        bank_guess = "PNC Bank (likely)"
    elif routing_number.startswith(("322", "062")):
        bank_guess = "Regions Bank (likely)"
    
    return {
        "valid": True,
        "bank_name": bank_guess or "Unknown Bank",
        "routing_number": routing_number,
        "region": region,
        "source": "pattern_match" if bank_guess else "region_only"
    }

def get_bank_suggestions(partial_routing):
    """
    Get bank suggestions based on partial routing number input
    """
    if not partial_routing or len(partial_routing) < 3:
        return []
    
    suggestions = []
    for routing, bank in BANK_ROUTING_DATABASE.items():
        if routing.startswith(partial_routing):
            suggestions.append({
                "routing_number": routing,
                "bank_name": bank,
                "formatted_routing": f"{routing[:3]}-{routing[3:6]}-{routing[6:]}"
            })
    
    # Sort by bank name and limit results
    suggestions.sort(key=lambda x: x["bank_name"])
    return suggestions[:10]  # Limit to 10 suggestions