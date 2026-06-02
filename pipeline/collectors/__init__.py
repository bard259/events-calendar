"""Collector registry — order = collection order in the orchestrator."""
from collectors.macro import MacroCollector, MacroNewsCollector
from collectors.central_bank import CentralBankCollector, IntlCentralBankCollector
from collectors.corporate_financial import CorporateFinancialCollector
from collectors.corporate_strategic import CorporateStrategicCollector
from collectors.operational import OperationalCollector
from collectors.regulatory import RegulatoryCollector
from collectors.industry import EiaCollector, IndustryNewsCollector
from collectors.geopolitical import GeopoliticalCollector
from collectors.news import StrategicNewsCollector, GeopoliticalNewsCollector
from collectors.ipo import IpoEdgarCollector, IpoNewsCollector
from collectors.ai_industry import AiIndustryCollector
from collectors.daily_news import DailyTechNewsCollector
from collectors.official_events import OfficialEventsCollector

ALL_COLLECTORS = [
    MacroCollector,              # 1  Tier 1: BLS + BEA parsed schedules
    MacroNewsCollector,          # 1  Tier 3: ISM/ADP/CB news-mined
    CentralBankCollector,        # 2  Tier 1: Fed FOMC parsed
    IntlCentralBankCollector,    # 2  Tier 3: ECB/BoE/BoJ news-mined
    CorporateFinancialCollector, # 3  live API + Tier 2 SEC full-text
    CorporateStrategicCollector, # 4  Tier 3: news-mined product/AI/M&A events
    OperationalCollector,        # 5  live API (Launch Library 2)
    RegulatoryCollector,         # 6  live API + Tier 2 SEC full-text PDUFA
    EiaCollector,                # 7  Tier 1: EIA energy release schedule
    IndustryNewsCollector,       # 7  Tier 3: OPEC/sector/shipping news
    GeopoliticalCollector,       # 8  Tier 3: elections/summits/tariffs news
    IpoEdgarCollector,           # 3  IPOs: real dated (EDGAR)
    IpoNewsCollector,            # 3  IPOs: rumored marquee (news)
    AiIndustryCollector,         # 9  Tier 3: AI-ecosystem milestones (chips/models/DC)
    DailyTechNewsCollector,      # 3/4/5/9  REAL daily news mine, marquee tech catalysts
    OfficialEventsCollector,     # 4/9  Official-site scrape of flagship conference dates
]
