"""
Scraper for PrizePicks and Underdog Fantasy lines
Uses Selenium with proper rate limiting and user-agent rotation to avoid bans
"""
import time
import random
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
from datetime import datetime

# User agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def setup_driver(headless: bool = True):
    """Setup Chrome driver with anti-detection options"""
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")
    
    # Anti-detection options
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        # Remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        print("Make sure ChromeDriver is installed and in PATH")
        return None


def scrape_prizepicks(email: str, password: str) -> List[Dict]:
    """
    Scrape PrizePicks lines (requires login)
    
    Args:
        email: PrizePicks email
        password: PrizePicks password
    
    Returns:
        List of prop dicts with player name, prop type, line
    """
    driver = setup_driver(headless=False)  # Keep visible for login
    if not driver:
        return []
    
    props = []
    
    try:
        print("Navigating to PrizePicks...")
        driver.get("https://app.prizepicks.com/")
        
        # Wait for login page or already logged in
        time.sleep(3)
        
        # Check if login is needed
        try:
            # Look for login elements
            login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log In') or contains(text(), 'Sign In')]")
            login_button.click()
            time.sleep(2)
            
            # Enter credentials
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            email_field.send_keys(email)
            
            password_field = driver.find_element(By.NAME, "password")
            password_field.send_keys(password)
            
            # Submit login
            submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_button.click()
            
            # Wait for login to complete
            time.sleep(5)
        except (NoSuchElementException, TimeoutException):
            print("Already logged in or login form not found")
        
        # Navigate to props page
        print("Looking for player props...")
        time.sleep(3)
        
        # PrizePicks structure: Look for prop cards
        # This is a simplified version - actual structure may vary
        prop_cards = driver.find_elements(By.CSS_SELECTOR, "[class*='prop'], [class*='card'], [data-testid*='prop']")
        
        for card in prop_cards[:20]:  # Limit to first 20 to avoid timeout
            try:
                # Extract player name, prop type, and line
                # Adjust selectors based on actual PrizePicks HTML structure
                player_name = card.find_element(By.CSS_SELECTOR, "[class*='player'], [class*='name']").text
                prop_text = card.find_element(By.CSS_SELECTOR, "[class*='prop'], [class*='stat']").text
                line_text = card.find_element(By.CSS_SELECTOR, "[class*='line'], [class*='total']").text
                
                # Parse prop type and line
                # Example: "Points Over 25.5" -> prop_type: "points", line: 25.5, side: "over"
                prop_type = None
                line = None
                side = None
                
                if "points" in prop_text.lower() or "pts" in prop_text.lower():
                    prop_type = "points"
                elif "rebounds" in prop_text.lower() or "reb" in prop_text.lower():
                    prop_type = "rebounds"
                elif "assists" in prop_text.lower() or "ast" in prop_text.lower():
                    prop_type = "assists"
                elif "pra" in prop_text.lower():
                    prop_type = "pra"
                elif "threes" in prop_text.lower() or "3pm" in prop_text.lower():
                    prop_type = "threes"
                
                if "over" in prop_text.lower():
                    side = "over"
                elif "under" in prop_text.lower():
                    side = "under"
                
                # Extract line number
                import re
                line_match = re.search(r'(\d+\.?\d*)', line_text)
                if line_match:
                    line = float(line_match.group(1))
                
                if player_name and prop_type and line:
                    props.append({
                        "player_name": player_name,
                        "prop_type": prop_type,
                        "line": line,
                        "side": side,
                        "source": "prizepicks",
                        "scraped_at": datetime.now().isoformat()
                    })
            except Exception as e:
                continue  # Skip cards that can't be parsed
        
        print(f"Scraped {len(props)} props from PrizePicks")
        
    except Exception as e:
        print(f"Error scraping PrizePicks: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
    
    return props


def scrape_underdog(email: str, password: str) -> List[Dict]:
    """
    Scrape Underdog Fantasy lines (requires login)
    
    Args:
        email: Underdog email
        password: Underdog password
    
    Returns:
        List of prop dicts with player name, prop type, line
    """
    driver = setup_driver(headless=False)  # Keep visible for login
    if not driver:
        return []
    
    props = []
    
    try:
        print("Navigating to Underdog Fantasy...")
        driver.get("https://underdogfantasy.com/")
        
        time.sleep(3)
        
        # Login logic similar to PrizePicks
        # Adjust selectors based on actual Underdog HTML structure
        try:
            login_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Log In') or contains(text(), 'Sign In')]")
            login_button.click()
            time.sleep(2)
            
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            email_field.send_keys(email)
            
            password_field = driver.find_element(By.NAME, "password")
            password_field.send_keys(password)
            
            submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_button.click()
            
            time.sleep(5)
        except (NoSuchElementException, TimeoutException):
            print("Already logged in or login form not found")
        
        # Navigate to props and scrape
        print("Looking for player props...")
        time.sleep(3)
        
        # Underdog structure: Look for prop elements
        # Adjust selectors based on actual structure
        prop_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='prop'], [class*='pick'], [data-testid*='prop']")
        
        for element in prop_elements[:20]:
            try:
                # Extract data (adjust based on actual HTML structure)
                player_name = element.find_element(By.CSS_SELECTOR, "[class*='player']").text
                prop_text = element.find_element(By.CSS_SELECTOR, "[class*='stat']").text
                line_text = element.find_element(By.CSS_SELECTOR, "[class*='line']").text
                
                # Parse similar to PrizePicks
                prop_type = None
                line = None
                side = None
                
                if "points" in prop_text.lower():
                    prop_type = "points"
                elif "rebounds" in prop_text.lower():
                    prop_type = "rebounds"
                elif "assists" in prop_text.lower():
                    prop_type = "assists"
                
                if "over" in prop_text.lower():
                    side = "over"
                elif "under" in prop_text.lower():
                    side = "under"
                
                import re
                line_match = re.search(r'(\d+\.?\d*)', line_text)
                if line_match:
                    line = float(line_match.group(1))
                
                if player_name and prop_type and line:
                    props.append({
                        "player_name": player_name,
                        "prop_type": prop_type,
                        "line": line,
                        "side": side,
                        "source": "underdog",
                        "scraped_at": datetime.now().isoformat()
                    })
            except:
                continue
        
        print(f"Scraped {len(props)} props from Underdog")
        
    except Exception as e:
        print(f"Error scraping Underdog: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
    
    return props


def store_dfs_lines(props: List[Dict], game_id: Optional[str] = None):
    """Store DFS lines in database"""
    from services.db import supabase
    from rapidfuzz import process
    
    # Load all players once for efficient matching
    print("Loading players for matching...")
    all_players = supabase.table("players").select("id,name").execute().data
    player_names = {p["name"]: p["id"] for p in all_players}
    
    stored = 0
    skipped = 0
    
    for prop in props:
        try:
            player_name = prop['player_name']
            
            # Find player by name (exact match first, then fuzzy)
            player_id = None
            
            # Strategy 1: Exact match (case-insensitive)
            for db_name, db_id in player_names.items():
                if db_name.lower() == player_name.lower():
                    player_id = db_id
                    break
            
            # Strategy 2: Fuzzy match
            if not player_id:
                matches = process.extract(player_name, list(player_names.keys()), limit=1, score_cutoff=85)
                if matches:
                    matched_name = matches[0][0]
                    player_id = player_names[matched_name]
            
            if not player_id:
                skipped += 1
                if skipped <= 5:
                    print(f"  Player '{player_name}' not found in database")
                continue
            
            # Store DFS line
            record = {
                "player_id": player_id,
                "prop_type": prop["prop_type"],
                "line": prop["line"],
                "side": prop.get("side"),
                "source": prop["source"],
                "scraped_at": prop["scraped_at"]
            }
            
            if game_id:
                record["game_id"] = game_id
            
            # Insert or update (unique constraint on player_id, prop_type, line, source, game_id)
            try:
                supabase.table("dfs_lines").upsert(
                    record,
                    on_conflict="player_id,prop_type,line,source,game_id"
                ).execute()
                stored += 1
            except Exception as e:
                print(f"  Error upserting DFS line for {player_name}: {e}")
                continue
                
        except Exception as e:
            print(f"Error processing DFS line: {e}")
            continue
    
    print(f"Stored {stored} DFS lines, skipped {skipped} (player not found)")


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Get credentials from environment variables
    prizepicks_email = os.getenv("PRIZEPICKS_EMAIL")
    prizepicks_password = os.getenv("PRIZEPICKS_PASSWORD")
    underdog_email = os.getenv("UNDERDOG_EMAIL")
    underdog_password = os.getenv("UNDERDOG_PASSWORD")
    
    all_props = []
    
    if prizepicks_email and prizepicks_password:
        print("Scraping PrizePicks...")
        prizepicks_props = scrape_prizepicks(prizepicks_email, prizepicks_password)
        all_props.extend(prizepicks_props)
        # Rate limiting between sites
        time.sleep(random.uniform(5, 10))
    else:
        print("PrizePicks credentials not found in .env")
    
    if underdog_email and underdog_password:
        print("Scraping Underdog...")
        underdog_props = scrape_underdog(underdog_email, underdog_password)
        all_props.extend(underdog_props)
    else:
        print("Underdog credentials not found in .env")
    
    if all_props:
        store_dfs_lines(all_props)
        print(f"\nTotal props scraped: {len(all_props)}")
    else:
        print("No props scraped. Check credentials and website structure.")

