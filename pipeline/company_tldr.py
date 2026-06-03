"""Plain-English, one-line business/mission TL;DRs for the companies the app surfaces.

Keyed by ticker. This is sourced *reference* metadata (what a company does), used to
introduce a company on its event card instead of dumping financial jargon. It is not
event data. Long-tail tickers (the full earnings calendar) that aren't here fall back to
a clean "{name} ({ticker}) — {size}-cap company" line in export_for_app.py.

Keep each entry to one sentence describing the core business/mission.
"""
from __future__ import annotations

COMPANY_TLDR: dict[str, str] = {
    # Mega-cap tech / platforms
    "AAPL": "Apple — designs the iPhone, Mac and a large services business; consumer hardware + software.",
    "MSFT": "Microsoft — Windows, Office and Azure cloud; a leader in enterprise software and AI.",
    "AMZN": "Amazon — the largest U.S. e-commerce marketplace plus AWS, the top cloud platform.",
    "GOOGL": "Alphabet — Google Search, YouTube, Android and Google Cloud; ad-funded, AI via Gemini.",
    "NVDA": "Nvidia — designs the GPUs that power AI training and inference; the core AI-compute supplier.",
    "META": "Meta — Facebook, Instagram and WhatsApp; ad-funded social media investing heavily in AI and AR/VR.",
    "TSLA": "Tesla — electric vehicles and energy storage, with autonomy/robotaxi ambitions.",
    # Semiconductors / AI hardware
    "AVGO": "Broadcom — semiconductors for AI, networking and broadband, plus infrastructure software (VMware).",
    "AMD": "AMD — designs CPUs and GPUs; Nvidia's main rival in AI accelerators.",
    "MU": "Micron — memory chips (DRAM/NAND), including the HBM used in AI accelerators.",
    "TSM": "TSMC — the world's largest contract chipmaker; fabricates leading-edge AI silicon.",
    "INTC": "Intel — designs and manufactures CPUs and is building a contract-foundry business.",
    "QCOM": "Qualcomm — mobile chipsets (Snapdragon) and wireless patents, expanding into auto and IoT.",
    "MRVL": "Marvell — data-center and custom-silicon chips for AI and networking.",
    "ARM": "Arm Holdings — licenses the CPU designs inside most smartphones and, increasingly, data centers.",
    "SMCI": "Super Micro — builds AI servers and data-center systems around Nvidia and AMD chips.",
    "DELL": "Dell — PCs and enterprise servers/storage; a major AI-server vendor.",
    "HPE": "Hewlett Packard Enterprise — servers, storage and networking for enterprises and AI.",
    "ANET": "Arista Networks — high-speed switches for cloud and AI data-center networks.",
    "CSCO": "Cisco — enterprise networking, security and collaboration hardware and software.",
    "VRT": "Vertiv — power and cooling infrastructure for data centers; an AI build-out supplier.",
    "AMAT": "Applied Materials — makes the equipment used to manufacture semiconductors.",
    "LRCX": "Lam Research — wafer-fabrication equipment for chip manufacturing.",
    "KLAC": "KLA — process-control and inspection tools for semiconductor fabs.",
    "ASML": "ASML — the sole maker of EUV lithography machines essential to advanced chips.",
    # Cloud / enterprise software
    "ORCL": "Oracle — enterprise databases and a fast-growing cloud-infrastructure business for AI workloads.",
    "CRWV": "CoreWeave — a GPU cloud that rents Nvidia compute to AI labs.",
    "PLTR": "Palantir — data-analytics and AI software for governments and enterprises.",
    "SNOW": "Snowflake — a cloud data platform for analytics and AI.",
    "NOW": "ServiceNow — cloud workflow-automation software for enterprise IT and operations.",
    "CRM": "Salesforce — the leading cloud CRM platform, expanding into AI agents.",
    "ADBE": "Adobe — creative and document software (Photoshop, Acrobat), adding generative AI.",
    "PANW": "Palo Alto Networks — cybersecurity platforms for network, cloud and security operations.",
    "ACN": "Accenture — global IT consulting and technology services.",
    # Defense / aerospace / space
    "RKLB": "Rocket Lab — small-launch rockets and spacecraft systems (our SpaceX proxy).",
    "LMT": "Lockheed Martin — the largest U.S. defense contractor (aircraft, missiles, space).",
    "RTX": "RTX (Raytheon) — defense systems plus Pratt & Whitney aircraft engines.",
    "NOC": "Northrop Grumman — defense and aerospace (bombers, space, missiles).",
    "BA": "Boeing — commercial jets and defense/space systems.",
    # Energy
    "XOM": "ExxonMobil — integrated oil & gas (exploration, refining, chemicals).",
    "CVX": "Chevron — integrated oil & gas major.",
    "COP": "ConocoPhillips — oil & gas exploration and production.",
    "BP": "BP — integrated energy major shifting toward lower-carbon.",
    "GASS": "StealthGas — shipping company transporting LPG and petrochemical gases.",
    # Autos / financials / health
    "F": "Ford — legacy automaker transitioning toward EVs and software.",
    "GM": "General Motors — automaker (Chevrolet, GMC, Cadillac) investing in EVs and autonomy.",
    "JPM": "JPMorgan Chase — the largest U.S. bank by assets.",
    "JNJ": "Johnson & Johnson — pharmaceuticals and medical technology.",
    "FDX": "FedEx — global package delivery and logistics.",
    # Consumer / retail (setup & earnings names)
    "VSXY": "Victoria's Secret — intimates, lingerie and beauty retailer (VS & PINK brands).",
    "CTRN": "Citi Trends — value-priced apparel and home goods for family/value shoppers.",
    "CAL": "Caleres — footwear company; owns Famous Footwear plus Sam Edelman and Naturalizer.",
    "KSS": "Kohl's — mid-tier department-store retailer.",
    "M": "Macy's — department-store retailer (Macy's, Bloomingdale's).",
    "NKE": "Nike — the world's largest athletic footwear and apparel brand.",
    "COST": "Costco — membership warehouse-club retailer.",
    "WMT": "Walmart — the largest U.S. retailer; stores plus growing e-commerce and ads.",
    # Other named in the data
    "CRON": "Cronos Group — a cannabis company with a large cash balance and global brands.",
    "PLUS": "ePlus — IT solutions and services (infrastructure, security, AI services).",
    "GEF": "Greif — industrial packaging (steel/plastic drums, IBCs) for global supply chains.",
}


def get_tldr(ticker: str) -> str:
    return COMPANY_TLDR.get((ticker or "").strip().upper(), "")
