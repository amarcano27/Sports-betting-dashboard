"""
APEX ANALYTICS - Core UI Components
Reusable HTML/CSS components for the ultimate betting dashboard.
"""
import streamlit as st
import html
from dashboard.premium_styles import TOKENS

def format_odds(odds):
    """Format American odds with +/-"""
    if odds is None or odds == "": return "—"
    try:
        v = int(odds)
        return f"+{v}" if v > 0 else str(v)
    except:
        return str(odds)

def render_metric_card(label: str, value: str, delta: str = None, color_type: str = "neutral"):
    """Render a sleek, isolated metric card."""
    c_map = {
        "success": TOKENS["green"],
        "danger": TOKENS["red"],
        "info": TOKENS["cyan"],
        "warning": TOKENS["amber"],
        "neutral": TOKENS["text_primary"]
    }
    main_color = c_map.get(color_type, TOKENS["text_primary"])
    
    delta_html = ""
    if delta:
        d_color = TOKENS["text_secondary"]
        if "+" in str(delta) or ("EV" in str(delta) and "-" not in str(delta)):
            d_color = TOKENS["green"]
        elif "-" in str(delta):
            d_color = TOKENS["red"]
            
        delta_html = f'<div style="color: {d_color}; font-size: 13px; font-weight: 700; margin-top: 4px; font-family: \'JetBrains Mono\', monospace;">{html.escape(str(delta))}</div>'

    html_content = f"""
    <div class="apex-card" style="padding: 16px;">
        <div style="color: {TOKENS['text_muted']}; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 8px;">
            {html.escape(label)}
        </div>
        <div style="color: {main_color}; font-size: 28px; font-weight: 800; font-family: 'JetBrains Mono', monospace; line-height: 1.1;">
            {html.escape(str(value))}
        </div>
        {delta_html}
    </div>
    """
    st.markdown(html_content.replace('\n', ''), unsafe_allow_html=True)

def render_prop_card(player_name, team, opponent, game_time, prop_type, line, over_odds, under_odds, model_proj, edge_pct, image_url=None):
    """Render the ultimate player prop card (PrizePicks/Action Network hybrid)."""
    # Escaping
    p_name = html.escape(str(player_name))
    t_team = html.escape(str(team))
    t_opp = html.escape(str(opponent))
    g_time = html.escape(str(game_time))
    p_type = html.escape(str(prop_type).upper().replace("_", " "))
    
    over_str = format_odds(over_odds)
    under_str = format_odds(under_odds)
    
    # Edge logic
    if edge_pct > 0:
        edge_color = TOKENS["green"]
        edge_str = f"+{edge_pct:.1f}%"
        glow_class = "glow-green"
    elif edge_pct < 0:
        edge_color = TOKENS["red"]
        edge_str = f"{edge_pct:.1f}%"
        glow_class = ""
    else:
        edge_color = TOKENS["text_secondary"]
        edge_str = "0.0%"
        glow_class = ""

    # Avatar
    initial = p_name[0] if p_name else "?"
    if image_url:
        img_url = html.escape(str(image_url))
        avatar = f"""
        <img src="{img_url}" style="width: 48px; height: 48px; border-radius: 8px; object-fit: cover; border: 1px solid {TOKENS['border_strong']};" 
             onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
        <div style="width: 48px; height: 48px; background: {TOKENS['bg_panel_2']}; border-radius: 8px; display: none; align-items: center; justify-content: center; font-weight: 800; color: {TOKENS['text_secondary']}; font-size: 20px; border: 1px solid {TOKENS['border_strong']};">{initial}</div>
        """
    else:
        avatar = f'<div style="width: 48px; height: 48px; background: {TOKENS["bg_panel_2"]}; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 800; color: {TOKENS["text_secondary"]}; font-size: 20px; border: 1px solid {TOKENS["border_strong"]};">{initial}</div>'

    card_html = f"""
    <div class="apex-card {glow_class}" style="padding: 16px; margin-bottom: 16px;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
            <div style="display: flex; gap: 12px; align-items: center;">
                {avatar}
                <div>
                    <div style="font-family: 'Inter', sans-serif; font-weight: 800; font-size: 16px; color: {TOKENS['text_primary']}; letter-spacing: -0.02em;">{p_name}</div>
                    <div style="font-family: 'Inter', sans-serif; font-size: 12px; color: {TOKENS['text_muted']}; margin-top: 2px; font-weight: 500;">
                        <span style="color: {TOKENS['text_secondary']};">{t_team}</span> vs {t_opp} • {g_time}
                    </div>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 10px; font-weight: 800; color: {TOKENS['text_muted']}; text-transform: uppercase; letter-spacing: 0.05em;">Edge</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 800; color: {edge_color};">{edge_str}</div>
            </div>
        </div>
        <!-- Line & Projection -->
        <div style="background: {TOKENS['bg_main']}; border-radius: 8px; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; border: 1px solid {TOKENS['border']}; margin-bottom: 12px;">
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 11px; color: {TOKENS['text_muted']}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">{p_type}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 800; color: {TOKENS['text_primary']};">{line}</div>
            </div>
            <div style="width: 1px; height: 30px; background: {TOKENS['border']}; margin: 0 12px;"></div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 11px; color: {TOKENS['text_muted']}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">Model Proj</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 20px; font-weight: 800; color: {TOKENS['cyan']};">{model_proj:.1f}</div>
            </div>
        </div>
        <!-- Odds Buttons -->
        <div style="display: flex; gap: 8px;">
            <div style="flex: 1; background: {TOKENS['bg_panel_2']}; border: 1px solid {TOKENS['border_strong']}; border-radius: 8px; padding: 10px; text-align: center; transition: all 0.2s; cursor: pointer;" onmouseover="this.style.borderColor='{TOKENS['green']}'; this.style.background='{TOKENS['green_bg']}';" onmouseout="this.style.borderColor='{TOKENS['border_strong']}'; this.style.background='{TOKENS['bg_panel_2']}';">
                <div style="font-size: 11px; font-weight: 800; color: {TOKENS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.05em;">Over</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 800; color: {TOKENS['green']}; margin-top: 2px;">{over_str}</div>
            </div>
            <div style="flex: 1; background: {TOKENS['bg_panel_2']}; border: 1px solid {TOKENS['border_strong']}; border-radius: 8px; padding: 10px; text-align: center; transition: all 0.2s; cursor: pointer;" onmouseover="this.style.borderColor='{TOKENS['red']}'; this.style.background='{TOKENS['red_bg']}';" onmouseout="this.style.borderColor='{TOKENS['border_strong']}'; this.style.background='{TOKENS['bg_panel_2']}';">
                <div style="font-size: 11px; font-weight: 800; color: {TOKENS['text_secondary']}; text-transform: uppercase; letter-spacing: 0.05em;">Under</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 800; color: {TOKENS['red']}; margin-top: 2px;">{under_str}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(card_html.replace('\n', ''), unsafe_allow_html=True)

def render_game_card(sport, away_team, home_team, time_str, away_ml, home_ml, edge_pct, recommendation, model_prob, market_prob):
    """Render the ultimate game analysis card."""
    a_ml_str = format_odds(away_ml)
    h_ml_str = format_odds(home_ml)
    
    # Badge logic
    badge_class = "badge-cyan"
    if recommendation in ["BEST VALUE", "STRONG", "PLAY"]: badge_class = "badge-green"
    elif recommendation in ["LEAN", "VALUE"]: badge_class = "badge-amber"
    elif recommendation in ["SKIP", "TRAP"]: badge_class = "badge-red"
    
    edge_color = TOKENS["green"] if edge_pct > 0 else TOKENS["red"]
    
    html_content = f"""
    <div class="apex-card" style="padding: 0; margin-bottom: 20px;">
        <!-- Header -->
        <div style="background: {TOKENS['bg_panel_2']}; padding: 12px 20px; border-bottom: 1px solid {TOKENS['border']}; display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 12px; font-weight: 800; color: {TOKENS['text_muted']}; text-transform: uppercase; letter-spacing: 0.1em;">
                {sport} • {time_str}
            </div>
            <div class="badge {badge_class}">{recommendation}</div>
        </div>
        <!-- Body -->
        <div style="padding: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="font-size: 20px; font-weight: 800; color: {TOKENS['text_primary']};">{away_team}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 800; color: {TOKENS['text_secondary']};">{a_ml_str}</div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <div style="font-size: 20px; font-weight: 800; color: {TOKENS['text_primary']};">@ {home_team}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 800; color: {TOKENS['text_secondary']};">{h_ml_str}</div>
            </div>
            <!-- Analysis Footer -->
            <div style="background: {TOKENS['bg_main']}; border-radius: 8px; padding: 12px; border: 1px solid {TOKENS['border']}; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 11px; color: {TOKENS['text_muted']}; font-weight: 700; text-transform: uppercase;">Model vs Market</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 13px; color: {TOKENS['text_secondary']}; margin-top: 2px;">
                        {model_prob*100:.1f}% vs {market_prob*100:.1f}%
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; color: {TOKENS['text_muted']}; font-weight: 700; text-transform: uppercase;">Edge</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 800; color: {edge_color};">
                        {'+' if edge_pct>0 else ''}{edge_pct:.1f}%
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(html_content.replace('\n', ''), unsafe_allow_html=True)
