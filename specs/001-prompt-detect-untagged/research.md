# Research and Decisions for SBIR Transition Detection

**Feature**: Detect Untagged SBIR Phase III Transitions
**Date**: 2025-10-15

This document records the decisions made to resolve ambiguities before implementation.

## 1. Data Access Strategy for USAspending and FPDS

- **Unknown**: The feature specification requires data from USAspending and FPDS but does not specify the access method. The primary need is to backtest against multiple fiscal years (FY20-FY24), which represents a very large dataset. The two main options are using the official APIs or downloading the bulk data archives.

- **Task**: Research the most efficient and reliable method for ingesting large volumes of historical federal spending data for the purpose of a one-time backtest.

### Decision: Use Bulk Downloads

For the initial implementation and backtesting, the system will rely exclusively on the bulk data downloads provided by USAspending.gov.

### Rationale:

1.  **Efficiency for Large Datasets**: The backtesting scope covers five years of data. API-based retrieval would require millions of requests, complex pagination logic, and would be subject to rate limiting, making it slow and unreliable for this scale. Bulk downloads provide the complete dataset in a compressed format, which is significantly faster to acquire.
2.  **Simplicity**: Processing a local CSV or database dump is computationally simpler than managing a high volume of network requests and their potential failures. This simplifies the data ingestion pipeline for the core backtesting feature.
3.  **Reproducibility**: Using a static data dump for a specific fiscal year ensures that the backtest is reproducible and the results are consistent. An API could return slightly different data over time.

## 2. Data Access Strategy for SBIR.gov Data

- **Update**: The user has provided a local file, `award_data.csv`, containing bulk data for SBIR Phase I and II awards.

### Decision: Use Local CSV File

The system will source all SBIR award data directly from the `award_data.csv` file located in the project root directory.

### Rationale:

1.  **Data Provided**: The user has explicitly provided this file as the source of truth for SBIR awards.
2.  **Efficiency**: Using a local CSV is the most efficient method for ingestion, avoiding any network requests or API dependencies for this part of the data.
3.  **Constraint**: The file is too large to inspect its schema directly via tools, so the implementation will have to assume the file contains the necessary columns as defined in the data model. The ingestion script will need to be robust enough to handle potential schema mismatches.

---

### Alternatives Considered:

-   **API-Only**: Rejected due to the scale of the backtest. This approach would be more suitable for a production system that needs to process ongoing, near-real-time data, but it is not practical for the primary requirement of historical analysis.
-   **Hybrid Approach**: Using bulk data for the initial load and APIs for updates. This is a sound strategy for a production system but adds unnecessary complexity for the current scope, which is focused on delivering the backtesting capability. We will proceed with a bulk-only approach to start.
