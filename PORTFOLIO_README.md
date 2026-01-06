# Sports Betting Analytics Platform
## Professional E-Portfolio Showcase

> **A comprehensive, data-driven sports betting analytics platform featuring real-time odds aggregation, ML-powered player projections, and automated value identification.**

---

## 🚀 Live Demo

Access the platform at: **http://localhost:8501**

**Default Landing Page**: Portfolio Showcase - Overview of all capabilities

---

## 💎 Key Features

### 1. **Real-Time Odds Aggregation**
- Multi-sportsbook odds comparison (DraftKings, FanDuel, BetMGM, Caesars, Bet365)
- Live odds tracking across NBA, NFL, MLB, NHL, NCAAB, NCAAF, and Esports
- Historical odds snapshots for trend analysis
- Line movement tracking

### 2. **Advanced Player Projections**
- Custom ML models for player performance prediction
- Injury impact analysis and rest day adjustments
- Matchup-based statistical modeling
- Confidence scoring system
- Projection vs. book line comparison

### 3. **Expected Value (EV) Analysis**
- Automated EV calculation for every bet
- Edge identification and visualization
- Positive EV filtering and sorting
- Risk-adjusted recommendations
- DEGEN mode for high-risk, high-reward plays

### 4. **AI-Powered Insights**
- Context-aware game analysis
- Player trend identification
- Smart parlay suggestions
- Automated bet slip generation
- Risk profile matching

### 5. **Interactive Data Visualization**
- Real-time performance charts
- Player trend sparklines
- Hit rate analysis
- Edge distribution graphs
- Market movement tracking

### 6. **Automated Data Pipeline**
- Scheduled API data fetching
- Error handling and retry logic
- Data validation and cleaning
- Snapshot management system
- Fallback to demo data when offline

---

## 🎨 Premium UI/UX

### Million-Dollar Design System
- **Gradient Backgrounds**: Multi-layer radial gradients with subtle animations
- **Glass Morphism**: Backdrop blur effects on cards and modals
- **Smooth Animations**: Cubic-bezier transitions for premium feel
- **Hover Effects**: Interactive card transformations with glow effects
- **Custom Scrollbars**: Gradient scrollbars with hover states
- **Typography**: Inter font family with gradient text effects
- **Color Palette**: Cyan (#00E5FF), Purple (#8A2BE2), Pink (#FF2E63)

### Responsive Components
- Adaptive grid layouts
- Mobile-friendly design
- Touch-optimized interactions
- Dynamic content loading
- Skeleton loading states

---

## 📊 Data Architecture

### Database Schema (Supabase/PostgreSQL)
```
├── games                    # Game schedules and metadata
├── players                  # Player profiles and stats
├── odds_snapshots          # Historical odds data
├── player_prop_odds        # Player prop markets
├── prop_feed_snapshots     # Precomputed prop analysis
├── player_injuries         # Injury reports and status
└── player_stats            # Historical performance data
```

### API Integrations
- **The Odds API**: Live odds and lines
- **NBA Stats API**: Player statistics
- **PandaScore API**: Esports data
- **HLTV API**: CS2 statistics

### Data Flow
```
APIs → Workers → Database → Cache → Dashboard
                     ↓
              Demo Data (Fallback)
```

---

## 🛠️ Technical Stack

### Backend
- **Python 3.11+**: Core language
- **Streamlit**: Web framework
- **Supabase**: PostgreSQL database + Auth
- **Pandas/NumPy**: Data processing
- **RapidFuzz**: Fuzzy matching

### Frontend
- **Streamlit Components**: Interactive UI
- **Plotly**: Data visualization
- **Custom CSS/HTML**: Premium styling
- **JavaScript**: Advanced interactions

### ML/Analytics
- **Scikit-learn**: Machine learning models
- **Custom Algorithms**: Projection calculations
- **Statistical Analysis**: EV and probability models

### Infrastructure
- **Scheduled Workers**: Automated data fetching
- **Error Handling**: Robust retry logic
- **Caching**: Multi-level caching strategy
- **Fallback System**: Demo data for offline mode

---

## 📁 Project Structure

```
sports-betting-dashboard/
├── dashboard/                  # Frontend application
│   ├── main.py                # Entry point
│   ├── portfolio_showcase.py # Landing page
│   ├── home_page.py           # Marketplace feed
│   ├── player_props_page.py  # Props analysis
│   ├── line_shopping.py       # Odds comparison
│   ├── premium_styles.py      # Million-dollar UI
│   ├── ui_components.py       # Reusable components
│   ├── data_loaders.py        # Data fetching logic
│   └── demo_data_loader.py    # Fallback data
│
├── services/                   # Backend services
│   ├── db.py                  # Database client
│   ├── odds_api.py            # Odds API integration
│   ├── projections.py         # ML projections
│   ├── ai_analysis.py         # AI insights
│   └── context_analysis.py    # Context evaluation
│
├── workers/                    # Background jobs
│   ├── fetch_odds.py          # Odds fetching
│   ├── fetch_player_prop_odds.py
│   ├── build_projection_snapshots.py
│   ├── build_prop_feed_snapshots.py
│   └── archive_all_data.py    # Data archiving
│
├── utils/                      # Utility functions
│   ├── ev.py                  # EV calculations
│   ├── analysis.py            # Statistical analysis
│   └── team_mapping.py        # Team normalization
│
├── data_archive/               # Permanent data storage
│   └── demo_data.json         # Demo dataset
│
└── requirements.txt            # Dependencies
```

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone repository
git clone <repository-url>
cd sports-betting-dashboard

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Create .env file
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
ODDS_API_KEY=your_odds_api_key
```

### 3. Run Dashboard
```bash
# Option 1: Direct run
streamlit run dashboard/main.py

# Option 2: Batch file (Windows)
RUN_DASHBOARD.bat
```

### 4. Access Application
Open browser to: **http://localhost:8501**

---

## 📈 Features Showcase

### Portfolio Landing Page
- Platform overview and capabilities
- Live data statistics
- Technical stack breakdown
- Feature highlights

### Marketplace Feed
- Real-time player props
- Edge calculations
- Projection overlays
- Filterable by sport, team, market
- Sort by edge, odds, or player

### Line Shopping
- Multi-book odds comparison
- Best odds identification
- Arbitrage opportunities
- Line movement tracking

### Player Props Analysis
- Detailed prop breakdowns
- Historical performance
- Hit rate analysis
- Matchup statistics

### Analytics Dashboard
- Performance tracking
- Trend analysis
- EV distribution
- ROI calculations

---

## 🎯 Use Cases

### For Portfolio Reviewers
- Demonstrates full-stack development skills
- Shows data pipeline architecture
- Highlights ML/AI integration
- Proves UI/UX design capabilities

### For Betting Enthusiasts
- Identifies value betting opportunities
- Provides data-driven insights
- Tracks performance over time
- Automates research process

### For Data Scientists
- Real-world ML application
- Statistical modeling examples
- Data visualization techniques
- ETL pipeline implementation

---

## 🔒 Data Privacy & Ethics

- **No Real Money**: Platform is for analysis only
- **Educational Purpose**: Demonstrates technical capabilities
- **Responsible Gaming**: Promotes informed decision-making
- **Data Security**: Secure API key management

---

## 📊 Performance Metrics

- **Data Freshness**: 5-minute cache TTL
- **API Response Time**: < 2 seconds average
- **UI Load Time**: < 1 second
- **Database Queries**: Optimized with indexing
- **Concurrent Users**: Supports multiple sessions

---

## 🎓 Learning Outcomes

### Technical Skills Demonstrated
- Full-stack Python development
- Database design and optimization
- API integration and management
- ML model development and deployment
- UI/UX design and implementation
- Data pipeline architecture
- Error handling and fallback systems
- Performance optimization

### Best Practices
- Clean code architecture
- Modular design patterns
- Comprehensive error handling
- User-centric design
- Documentation standards
- Version control (Git)

---

## 🚧 Future Enhancements

- [ ] Real-time WebSocket updates
- [ ] Mobile app (React Native)
- [ ] Advanced ML models (Deep Learning)
- [ ] Social features (bet sharing)
- [ ] Performance tracking dashboard
- [ ] API for third-party integration
- [ ] Multi-language support
- [ ] Dark/Light theme toggle

---

## 📞 Contact & Links

- **Portfolio**: [Your Portfolio URL]
- **GitHub**: [Your GitHub]
- **LinkedIn**: [Your LinkedIn]
- **Email**: [Your Email]

---

## 📝 License

This project is for portfolio demonstration purposes. All rights reserved.

---

## 🙏 Acknowledgments

- **The Odds API**: Odds data provider
- **Supabase**: Backend infrastructure
- **Streamlit**: Web framework
- **Open Source Community**: Various libraries and tools

---

**Built with ❤️ and Python** | **Last Updated**: January 2026


