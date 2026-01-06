import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys
import os
import argparse
import json
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from services.db import supabase
except ImportError:
    print("Error importing services.db. Ensure you are running from project root.")
    sys.exit(1)

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')  # Use new headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Randomize user agent if needed, but uc handles it well
    driver = uc.Chrome(options=options)
    return driver

def search_player(driver, player_name):
    print(f"Searching for {player_name}...")
    driver.get(f"https://www.hltv.org/search?query={player_name}")
    
    try:
        # Wait for search results
        # The first result under "Players" usually
        # Selector might be complex. Look for table with class 'table' or text "Players"
        # Usually /search returns a page with sections.
        
        # Wait for element
        wait = WebDriverWait(driver, 10)
        # Try to find the first link in the Players section
        # The layout: "Players" header, then a table.
        
        # Find the 'Players' header
        # xpath: //div[contains(text(), 'Players')]
        # Then find the next table
        
        # Simplified: Find first href containing "/player/"
        results = driver.find_elements(By.XPATH, "//a[contains(@href, '/player/')]")
        
        if not results:
            print("No player found.")
            return None
            
        # Click the first one? Or filter by exact name match?
        # Let's pick the first one for now.
        first_result = results[0]
        profile_url = first_result.get_attribute("href")
        print(f"Found profile: {profile_url}")
        return profile_url
        
    except Exception as e:
        print(f"Error searching player: {e}")
        return None

def scrape_stats(driver, profile_url, player_name, player_id_db):
    # Convert profile URL to stats URL
    # Profile: https://www.hltv.org/player/11893/zywoo
    # Stats Matches: https://www.hltv.org/stats/players/matches/11893/zywoo
    
    if "/player/" in profile_url:
        stats_url = profile_url.replace("/player/", "/stats/players/matches/")
    else:
        print("Invalid profile URL format.")
        return
        
    print(f"Navigating to stats: {stats_url}")
    driver.get(stats_url)
    time.sleep(2) # Be polite
    
    try:
        # Table rows: //table[contains(@class, 'stats-table')]/tbody/tr
        wait = WebDriverWait(driver, 10)
        rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//table[contains(@class, 'stats-table')]/tbody/tr")))
        
        print(f"Found {len(rows)} matches. Processing last 10...")
        
        stats_data = []
        
        for row in rows[:10]: # Limit to 10 to avoid ban/timeout
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) < 5:
                continue
                
            # Columns: Date, Team(vs), Opponent, Map, K-D, +/-, Rating
            # Example:
            # 0: Date (21/11/25)
            # 1: Team (Vitality)
            # 2: Opponent (FaZe)
            # 3: Map (Mirage)
            # 4: K-D (22 - 15)
            # 5: +/- (+7)
            # 6: Rating (1.45)
            
            date_str = cols[0].text.strip()
            # Parse date. Usually DD/MM/YY
            try:
                date_obj = datetime.strptime(date_str, "%d/%m/%y")
                date_iso = date_obj.isoformat()
            except:
                date_iso = datetime.now().isoformat() # Fallback
                
            opponent = cols[2].text.strip()
            map_name = cols[3].text.strip()
            kd_str = cols[4].text.strip()
            
            kills = 0
            deaths = 0
            if " - " in kd_str:
                parts = kd_str.split(" - ")
                kills = int(parts[0])
                deaths = int(parts[1])
            elif "-" in kd_str: # sometimes 22-15 without spaces
                 parts = kd_str.split("-")
                 if len(parts) == 2:
                     kills = int(parts[0])
                     deaths = int(parts[1])
            
            rating = cols[6].text.strip()
            
            # Construct DB record
            # Mapping: points->Kills, rebounds->Deaths, assists->0 (HLTV list view doesn't show assists easily without detail page)
            # To get assists, we'd need to click into the match. That's 10 more requests. Too risky.
            # We'll explicitly set assists to 0 or None to indicate missing.
            # Or estimate? No.
            
            record = {
                "player_id": player_id_db,
                "game_id": f"hltv_{date_iso}_{map_name}_{kills}", # Unique ID
                "date": date_iso,
                "points": kills,
                "rebounds": deaths,
                "assists": 0, # Missing in this view
                "opponent": opponent,
                "home": False, # Unknown
                "minutes_played": 0
            }
            stats_data.append(record)
            
        # Upsert to DB
        if stats_data:
            print(f"Upserting {len(stats_data)} records...")
            # Use a batch upsert if possible, or loop
            for rec in stats_data:
                # Check if exists? Upsert handles it.
                # We need to use the 'game_id' logic carefully. 
                # The schema key is usually (player_id, game_id).
                try:
                    supabase.table("player_game_stats").upsert(rec).execute()
                except Exception as e:
                    print(f"Error inserting: {e}")
            print("Success!")
        else:
            print("No stats extracted.")
            
    except Exception as e:
        print(f"Error scraping stats: {e}")

def main():
    parser = argparse.ArgumentParser(description='Scrape HLTV stats for a player')
    parser.add_argument('--player_name', required=True, help='Player name to search')
    parser.add_argument('--player_id', required=True, help='Supabase Player UUID')
    args = parser.parse_args()
    
    driver = None
    try:
        driver = get_driver()
        profile_url = search_player(driver, args.player_name)
        if profile_url:
            scrape_stats(driver, profile_url, args.player_name, args.player_id)
        else:
            print("Could not find player profile.")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()

