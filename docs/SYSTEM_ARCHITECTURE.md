# SBIR Transition Detection System - Architecture & Analysis

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES (14GB+ Production Scale)                   │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  📁 SBIR Awards (364MB)           │  📁 Federal Contracts (14GB)                    │
│  ├─ award_data.csv                │  ├─ FY2024_All_Contracts_Full_*.csv (7 files)  │
│  ├─ Company, Phase, Agency        │  ├─ PIID, Agency, Recipient, Dates             │
│  ├─ Award Date, Topic             │  ├─ Competition Details, Pricing               │
│  └─ Award Number, Amount          │  └─ Modifications, Transactions                │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER (Production Verified ✅)                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  🏗️  Standardized Data Ingestion Architecture                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                            INGESTER FACTORY                                     │ │
│  │  ┌─────────────────┬─────────────────┬─────────────────┬─────────────────────┐ │ │
│  │  │ Auto-Detection  │ File Validation │ Type Routing    │ Error Handling      │ │ │
│  │  │• Name patterns  │• Schema check   │• SBIR ingester  │• Graceful failures  │ │ │
│  │  │• Column analysis│• Required fields│• Contract       │• Detailed logging   │ │ │
│  │  │• Format hints   │• Data types     │  ingester       │• Recovery options   │ │ │
│  │  └─────────────────┴─────────────────┴─────────────────┴─────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                           │
│  📊 SbirIngester (Verified)              │  📋 ContractIngester (Verified)          │
│  ├─ BaseIngester interface               │  ├─ BaseIngester interface               │
│  ├─ Optimized pandas (engine='c')        │  ├─ Chunked processing (100K rows)      │
│  ├─ Date fallback logic                  │  ├─ Vectorized validation               │
│  ├─ Bulk vendor creation                  │  ├─ Streaming for large files           │
│  ├─ Award Year proxy recovery            │  ├─ Duplicate PIID handling             │
│  ├─ IngestionStats reporting             │  ├─ IngestionStats reporting            │
│  └─ 35K+ records/sec performance         │  └─ 150K+ records/sec performance       │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE LAYER (SQLite)                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  📊 Production Data (Current Scale)                                                 │
│  ┌─────────────────┬─────────────────┬─────────────────┬─────────────────────────┐ │
│  │   vendors       │  sbir_awards    │   contracts     │  vendor_identifiers     │ │
│  │   118,845       │    75,804       │  6,670,546      │     (cross-walk)        │ │
│  │                 │                 │                 │                         │ │
│  │ ┌─────────────┐ │ ┌─────────────┐ │ ┌─────────────┐ │ ┌─────────────────────┐ │ │
│  │ │id (PK)      │ │ │id (PK)      │ │ │id (PK)      │ │ │vendor_id (FK)       │ │ │
│  │ │name         │ │ │vendor_id(FK)│ │ │vendor_id(FK)│ │ │identifier_type      │ │ │
│  │ │created_at   │ │ │award_piid   │ │ │piid         │ │ │identifier_value     │ │ │
│  │ └─────────────┘ │ │phase        │ │ │agency       │ │ └─────────────────────┘ │ │
│  │                 │ │agency       │ │ │start_date   │ │                         │ │
│  │                 │ │award_date   │ │ │competition_ │ │                         │ │
│  │                 │ │completion_  │ │ │details      │ │                         │ │
│  │                 │ │date         │ │ └─────────────┘ │                         │ │
│  │                 │ │topic        │ │                 │                         │ │
│  │                 │ └─────────────┘ │                 │                         │ │
│  └─────────────────┴─────────────────┴─────────────────┴─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            DETECTION ENGINE (Core Logic)                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  🔍 Multi-Algorithm Detection Pipeline                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        DETECTION ALGORITHMS                                     │ │
│  │  ┌─────────────────┬─────────────────┬─────────────────┬─────────────────────┐ │ │
│  │  │ High Confidence │ Likely Signals  │ Cross-Service   │ Text Analysis       │ │ │
│  │  │                 │                 │                 │                     │ │ │
│  │  │• Same agency    │• Competed       │• Different      │• Description        │ │ │
│  │  │• Sole source    │  contracts      │  agencies       │  similarity         │ │ │
│  │  │• 24mo timing    │• Service        │• Department     │• Topic matching     │ │ │
│  │  │• Topic match    │  continuity     │  continuity     │• Keyword analysis   │ │ │
│  │  └─────────────────┴─────────────────┴─────────────────┴─────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                           │
│  🎯 YAML Configuration System            │  ⚡ Parallel Processing (4 workers)      │
│  ├─ Thresholds, weights, timing          │  ├─ 174,562 detections/minute           │
│  ├─ Feature toggles                       │  ├─ Batch processing optimization       │
│  └─ Detection parameters                  │  └─ Progress tracking & error handling  │
└─────────────────────────────────────────────────────────────────────────────────────┘