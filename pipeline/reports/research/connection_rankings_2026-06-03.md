# Connection rankings — Nvidia · SpaceX · Anthropic (2026-06-03)

Method: weighted 3-hop diffusion (0.5/hop) over curated ecosystem + stock graph. Score = summed decayed weighted relationship paths from the hub.
Each company is annotated with its next earnings call date (from the DB) + strongest link.

## Most connected to Nvidia  (42 connected companies)

| # | Ticker | Company | Score | Next earnings | Strongest link |
|--:|--------|---------|------:|---------------|----------------|
| 1 | **TSM** | TSMC | 43.2386 | 2026-07-16 | direct: supplies — fabs ~92% of advanced AI chips |
| 2 | **MSFT** | Microsoft (Azure) | 37.1465 | — | direct: supplies — GPUs |
| 3 | **AMZN** | Amazon (AWS) | 31.1669 | — | direct: supplies — GPUs |
| 4 | **MRVL** | Marvell | 25.9508 | — | direct: invests in — $2B; NVLink Fusion |
| 5 | **GOOGL** | Alphabet (Google Cloud) | 24.8062 | 2026-07-22 | direct: supplies — GPUs |
| 6 | **META** | Meta | 23.7992 | 2026-06-25 | direct: supplies — GPUs |
| 7 | **ORCL** | Oracle (OCI) | 22.2645 | 2026-06-10 | direct: supplies — GPUs |
| 8 | **MU** | Micron | 21.1779 | 2026-06-24 | direct: supplies — HBM |
| 9 | **SMCI** | Super Micro | 16.2255 | — | direct: partners — reference AI systems |
| 10 | **AVGO** | Broadcom | 15.9623 | 2026-06-03 | direct: event impact — Primary event company has a stock-imp |
| 11 | **CRWV** | CoreWeave | 15.597 | — | direct: supplies — GPUs |
| 12 | **AMD** | AMD | 14.4022 | — | via OpenAI (invests in / supplies) |
| 13 | **RMCF** | Rocky Mountain Chocolate Fac | 6.8154 | 2026-07-21 | direct: event impact — Primary event company has a stock-imp |
| 14 | **VRT** | Vertiv | 5.5935 | — | via CoreWeave (supplies / supplies) |
| 15 | **CEG** | Constellation Energy | 5.3112 | — | via Anthropic (invests in / powers) |
| 16 | **NXPI** | NXP Semiconductors N.V. | 5.2999 | 2026-07-20 | direct: event impact — Primary event company has a stock-imp |
| 17 | **CMG** | Chipotle Mexican Grill, Inc. | 5.2719 | 2026-07-22 | direct: event impact — Primary event company has a stock-imp |
| 18 | **ANET** | Arista | 5.229 | — | via Microsoft (Azure) (supplies / supplies) |
| 19 | **AMAT** | Applied Materials | 5.1503 | — | via TSMC (supplies / supplies) |
| 20 | **ASML** | ASML | 5.1503 | 2026-07-15 | via TSMC (supplies / supplies) |

## Most connected to SpaceX  (37 connected companies)

| # | Ticker | Company | Score | Next earnings | Strongest link |
|--:|--------|---------|------:|---------------|----------------|
| 1 | **MSFT** | Microsoft (Azure) | 4.249 | — | direct: partners — Starlink global internet |
| 2 | **NVDA** | Nvidia | 2.0495 | — | via Microsoft (Azure) (partners / supplies) |
| 3 | **AMZN** | Amazon (AWS) | 1.846 | — | multi-hop |
| 4 | **TSM** | TSMC | 1.683 | 2026-07-16 | via Microsoft (Azure) (partners / supplies) |
| 5 | **META** | Meta | 1.33 | 2026-06-25 | multi-hop |
| 6 | **MRVL** | Marvell | 1.224 | — | via Microsoft (Azure) (partners / supplies) |
| 7 | **GOOGL** | Alphabet (Google Cloud) | 1.171 | 2026-07-22 | multi-hop |
| 8 | **ORCL** | Oracle (OCI) | 1.17 | 2026-06-10 | multi-hop |
| 9 | **CRWV** | CoreWeave | 1.134 | — | multi-hop |
| 10 | **STM** | STMicroelectronics | 1.0676 | 2026-07-23 | direct: supplies — Starlink silicon (decade partnership) |
| 11 | **MU** | Micron | 1.0485 | 2026-06-24 | multi-hop |
| 12 | **AMD** | AMD | 0.855 | — | via Microsoft (Azure) (partners / supplies) |
| 13 | **AVGO** | Broadcom | 0.855 | 2026-06-03 | multi-hop |
| 14 | **SMCI** | Super Micro | 0.792 | — | via Microsoft (Azure) (partners / supplies) |
| 15 | **CEG** | Constellation Energy | 0.413 | — | via Microsoft (Azure) (partners / powers) |
| 16 | **CRM** | Salesforce Ventures | 0.361 | — | multi-hop |
| 17 | **ANET** | Arista | 0.36 | — | via Microsoft (Azure) (partners / supplies) |
| 18 | **VRT** | Vertiv | 0.36 | — | via Microsoft (Azure) (partners / supplies) |
| 19 | **AMAT** | Applied Materials | 0.324 | — | multi-hop |
| 20 | **ASML** | ASML | 0.324 | 2026-07-15 | multi-hop |

## Most connected to Anthropic  (43 connected companies)

| # | Ticker | Company | Score | Next earnings | Strongest link |
|--:|--------|---------|------:|---------------|----------------|
| 1 | **NVDA** | Nvidia | 20.1708 | — | direct: invests in — up to $10B |
| 2 | **MSFT** | Microsoft (Azure) | 19.65 | — | direct: invests in — up to $5B |
| 3 | **AMZN** | Amazon (AWS) | 16.9714 | — | direct: invests in — ~$8B + up to $25B (~$33B total) |
| 4 | **GOOGL** | Alphabet (Google Cloud) | 14.5951 | 2026-07-22 | direct: invests in — up to $40B |
| 5 | **TSM** | TSMC | 13.313 | 2026-07-16 | via Nvidia (invests in / supplies) |
| 6 | **AVGO** | Broadcom | 10.3748 | 2026-06-03 | direct: supplies — co-designs next-gen TPU compute |
| 7 | **MRVL** | Marvell | 9.6885 | — | via Nvidia (invests in / invests in) |
| 8 | **AMD** | AMD | 7.452 | — | via Microsoft (Azure) (supplies / supplies) |
| 9 | **META** | Meta | 6.781 | 2026-06-25 | via Nvidia (invests in / supplies) |
| 10 | **MU** | Micron | 5.883 | 2026-06-24 | via Nvidia (invests in / supplies) |
| 11 | **ORCL** | Oracle (OCI) | 5.823 | 2026-06-10 | via Nvidia (invests in / supplies) |
| 12 | **CRM** | Salesforce Ventures | 5.6382 | — | direct: invests in — Salesforce Ventures |
| 13 | **CRWV** | CoreWeave | 5.0985 | — | via Nvidia (invests in / supplies) |
| 14 | **SMCI** | Super Micro | 4.7295 | — | via Microsoft (Azure) (supplies / supplies) |
| 15 | **CEG** | Constellation Energy | 4.2822 | — | direct: powers — nuclear powers AWS/Azure AI capacity |
| 16 | **AMAT** | Applied Materials | 3.2355 | — | multi-hop |
| 17 | **ASML** | ASML | 3.2355 | 2026-07-15 | multi-hop |
| 18 | **KLAC** | KLA | 3.2355 | — | multi-hop |
| 19 | **LRCX** | Lam Research | 3.2355 | — | multi-hop |
| 20 | **RMCF** | Rocky Mountain Chocolate Fac | 2.5288 | 2026-07-21 | via Nvidia (invests in / event impact) |

