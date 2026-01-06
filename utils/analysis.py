"""
Analysis utilities for betting data
"""
from typing import List, Dict
from utils.ev import american_to_prob, ev


def calculate_bet_ev(price: int, true_prob: float = None) -> Dict:
    """
    Calculate expected value for a bet.
    
    Args:
        price: American odds (e.g., -110, +150)
        true_prob: True probability (if None, uses implied probability)
    
    Returns:
        Dictionary with EV metrics
    """
    implied_prob = american_to_prob(price)
    true_prob = true_prob or implied_prob
    
    ev_value = ev(true_prob, price)
    
    return {
        "price": price,
        "implied_prob": implied_prob,
        "true_prob": true_prob,
        "ev": ev_value,
        "edge": ev_value / implied_prob if implied_prob > 0 else 0
    }


def find_best_odds(odds_list: List[Dict]) -> Dict:
    """
    Find the best odds for each market across bookmakers.
    
    Args:
        odds_list: List of odds dictionaries
    
    Returns:
        Dictionary mapping market_label to best odds
    """
    best_odds = {}
    
    for odd in odds_list:
        market_key = f"{odd.get('market_type')}_{odd.get('market_label')}"
        price = odd.get("price")
        
        if price is None:
            continue
        
        if market_key not in best_odds:
            best_odds[market_key] = odd
        else:
            # For positive odds, higher is better
            # For negative odds, less negative is better (closer to 0)
            current_price = best_odds[market_key].get("price")
            if price > 0 and (current_price is None or price > current_price):
                best_odds[market_key] = odd
            elif price < 0 and (current_price is None or price > current_price):
                best_odds[market_key] = odd
    
    return best_odds


def suggest_pairings(bets: List[Dict], max_legs: int = 3, min_ev: float = 0.0) -> List[Dict]:
    """
    Suggest profitable bet pairings based on EV.
    
    Args:
        bets: List of bet dictionaries with EV calculated
        max_legs: Maximum number of legs in parlay
        min_ev: Minimum combined EV threshold
    
    Returns:
        List of suggested pairings
    """
    # Filter bets with positive EV
    positive_ev_bets = [b for b in bets if b.get("ev", 0) > min_ev]
    
    if len(positive_ev_bets) < 2:
        return []
    
    # Sort by EV
    positive_ev_bets.sort(key=lambda x: x.get("ev", 0), reverse=True)
    
    suggestions = []
    
    # Generate 2-leg combinations
    for i in range(len(positive_ev_bets)):
        for j in range(i + 1, len(positive_ev_bets)):
            leg1 = positive_ev_bets[i]
            leg2 = positive_ev_bets[j]
            
            # Calculate combined metrics
            combined_ev = (leg1.get("ev", 0) + leg2.get("ev", 0)) / 2
            
            # Calculate combined odds (simplified)
            price1 = leg1.get("price", 0)
            price2 = leg2.get("price", 0)
            
            if price1 and price2:
                # Convert to decimal odds
                if price1 > 0:
                    dec1 = price1 / 100 + 1
                else:
                    dec1 = 100 / abs(price1) + 1
                
                if price2 > 0:
                    dec2 = price2 / 100 + 1
                else:
                    dec2 = 100 / abs(price2) + 1
                
                combined_decimal = dec1 * dec2
                
                # Convert back to American
                if combined_decimal > 2:
                    combined_american = int((combined_decimal - 1) * 100)
                else:
                    combined_american = int(-100 / (combined_decimal / 100))
                
                if combined_ev >= min_ev:
                    suggestions.append({
                        "legs": [leg1, leg2],
                        "combined_ev": combined_ev,
                        "combined_odds": combined_american,
                        "combined_decimal": combined_decimal,
                        "num_legs": 2
                    })
    
    # Generate 3-leg combinations if requested
    if max_legs >= 3 and len(positive_ev_bets) >= 3:
        for i in range(len(positive_ev_bets)):
            for j in range(i + 1, len(positive_ev_bets)):
                for k in range(j + 1, len(positive_ev_bets)):
                    leg1 = positive_ev_bets[i]
                    leg2 = positive_ev_bets[j]
                    leg3 = positive_ev_bets[k]
                    
                    combined_ev = (leg1.get("ev", 0) + leg2.get("ev", 0) + leg3.get("ev", 0)) / 3
                    
                    if combined_ev >= min_ev:
                        suggestions.append({
                            "legs": [leg1, leg2, leg3],
                            "combined_ev": combined_ev,
                            "combined_odds": None,  # Calculate if needed
                            "combined_decimal": None,
                            "num_legs": 3
                        })
    
    # Sort by combined EV
    suggestions.sort(key=lambda x: x["combined_ev"], reverse=True)
    
    return suggestions


def calculate_parlay_odds(legs: List[Dict]) -> Dict:
    """
    Calculate combined odds for a parlay.
    
    Args:
        legs: List of bet legs with 'price' field
    
    Returns:
        Dictionary with parlay metrics
    """
    if not legs:
        return {"error": "No legs provided"}
    
    decimal_odds = 1.0
    valid_prices = []
    
    for leg in legs:
        price = leg.get("price")
        if price is None:
            continue
        
        if price > 0:
            decimal = price / 100 + 1
        else:
            decimal = 100 / abs(price) + 1
        
        decimal_odds *= decimal
        valid_prices.append(price)
    
    if not valid_prices:
        return {"error": "No valid prices"}
    
    # Convert to American odds
    if decimal_odds > 2:
        american_odds = int((decimal_odds - 1) * 100)
    else:
        american_odds = int(-100 / (decimal_odds / 100))
    
    implied_prob = 1 / decimal_odds
    
    return {
        "decimal_odds": decimal_odds,
        "american_odds": american_odds,
        "implied_probability": implied_prob,
        "num_legs": len(valid_prices)
    }

