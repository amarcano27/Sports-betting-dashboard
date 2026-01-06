"""
Custom Charts for the Million Dollar Dashboard
"""
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd

def create_prop_chart(games, prop_type, line, title="Player Prop Chart"):
    """
    Create a high-end bar chart showing player prop performance vs the line.
    """
    if not games:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(color="#888"))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        return fig
    
    # Prepare data
    dates = []
    values = []
    labels = []
    colors = []
    hover_texts = []
    
    for game in games:
        # Get game date
        game_date = game.get("date")
        if isinstance(game_date, str):
            try:
                date_obj = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
                dates.append(date_obj)
                date_str = date_obj.strftime("%b %d")
            except:
                dates.append(None)
                date_str = "N/A"
        else:
            dates.append(game_date)
            date_str = "N/A"
        
        # Get opponent
        opponent = game.get("opponent", "Unknown")
        home_away = "vs" if game.get("home", True) else "@"
        labels.append(f"{date_str}<br>{home_away} {opponent}")
        
        # Get prop value
        value = None
        if prop_type == "points":
            value = game.get("points", 0)
        elif prop_type == "rebounds":
            value = game.get("rebounds", 0)
        elif prop_type == "assists":
            value = game.get("assists", 0)
        elif prop_type == "pra":
            value = (game.get("points", 0) + 
                    game.get("rebounds", 0) + 
                    game.get("assists", 0))
        elif prop_type == "threes":
            value = game.get("threes", 0)
        
        values.append(value if value is not None else 0)
        
        # Color: Cyan if over line, Pink if under
        if value is not None and value > line:
            colors.append("#00E5FF")  # Cyan
        elif value is not None and value < line:
            colors.append("#FF2E63")  # Pink
        else:
            colors.append("#888888")  # Gray (Push)
            
        hover_texts.append(f"{date_str} {home_away} {opponent}<br>{prop_type.title()}: {value}")
    
    # Create chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=values,
        textposition="outside",
        textfont=dict(color='white', family="JetBrains Mono"),
        hovertext=hover_texts,
        hoverinfo="text",
        name=prop_type.title()
    ))
    
    # Add line
    fig.add_hline(
        y=line,
        line_dash="dash",
        line_color="white",
        line_width=1,
        annotation_text=f"Line: {line}",
        annotation_position="top right",
        annotation_font=dict(color="white", family="JetBrains Mono")
    )
    
    # Add trend line (Moving Average)
    if len(values) >= 3:
        df = pd.DataFrame({"value": values})
        df["ma"] = df["value"].rolling(window=5, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=labels,
            y=df["ma"],
            mode='lines',
            line=dict(color='rgba(255, 255, 255, 0.3)', width=2, dash='dot'),
            name='Trend (L5)',
            hoverinfo='skip'
        ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color="white", size=14, family="Inter"),
            x=0,
            y=0.95
        ),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(color="#888", size=10),
            tickangle=-45
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#222",
            gridwidth=1,
            tickfont=dict(color="#888")
        ),
        showlegend=False,
        height=350,
        margin=dict(l=20, r=20, t=40, b=60),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hoverlabel=dict(
            bgcolor="#141414",
            bordercolor="#333",
            font=dict(color="white", family="Inter")
        )
    )
    
    return fig


