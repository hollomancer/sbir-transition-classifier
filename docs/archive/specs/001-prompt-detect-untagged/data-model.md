# Data Model: SBIR Transition Detection

**Feature**: Detect Untagged SBIR Phase III Transitions
**Date**: 2025-10-15

This document defines the core data entities required for the feature. The model is designed for a relational database (e.g., PostgreSQL).

---

## Table: `vendors`

Represents a commercial entity receiving awards and contracts. This table serves as a central point for unifying vendor identity across different government systems.

| Column Name | Data Type | Description | Notes |
|---|---|---|---|
| `id` | `UUID` | Primary key for the vendor. | |
| `name` | `TEXT` | The name of the vendor. | |
| `created_at` | `TIMESTAMP` | Timestamp of record creation. | |
| `updated_at` | `TIMESTAMP` | Timestamp of last record update. | |

---

## Table: `vendor_identifiers`

Stores various identifiers associated with a vendor (UEI, CAGE, DUNS). This allows for cross-walking between different ID systems.

| Column Name | Data Type | Description | Notes |
|---|---|---|---|
| `id` | `UUID` | Primary key. | |
| `vendor_id` | `UUID` | Foreign key to `vendors.id`. | Indexed |
| `identifier_type` | `TEXT` | Type of identifier (e.g., 'UEI', 'CAGE', 'DUNS'). | |
| `identifier_value`| `TEXT` | The value of the identifier. | Indexed, Unique |
| `created_at` | `TIMESTAMP` | Timestamp of record creation. | |

---

## Table: `sbir_awards`

Represents a single SBIR Phase I or Phase II award.

| Column Name | Data Type | Description | Notes |
|---|---|---|---|
| `id` | `UUID` | Primary key. | |
| `vendor_id` | `UUID` | Foreign key to `vendors.id`. | Indexed |
| `award_piid` | `TEXT` | The unique identifier for the award. | |
| `phase` | `TEXT` | The SBIR phase (e.g., 'Phase I', 'Phase II'). | |
| `agency` | `TEXT` | The awarding agency. | |
| `award_date` | `DATE` | The date the award was made. | |
| `completion_date`| `DATE` | The period of performance end date. | Indexed |
| `topic` | `TEXT` | The SBIR topic associated with the award. | |
| `raw_data` | `JSONB` | The complete source record from SBIR.gov. | |
| `created_at` | `TIMESTAMP` | Timestamp of record creation. | |

---

## Table: `contracts`

Represents a federal contract vehicle or standalone contract from FPDS/USAspending.

| Column Name | Data Type | Description | Notes |
|---|---|---|---|
| `id` | `UUID` | Primary key. | |
| `vendor_id` | `UUID` | Foreign key to `vendors.id`. | Indexed |
| `piid` | `TEXT` | The unique identifier for the contract. | Unique, Indexed |
| `parent_piid` | `TEXT` | The PIID of the parent IDV, if applicable. | Indexed |
| `agency` | `TEXT` | The awarding agency/office. | |
| `start_date` | `DATE` | The start date of the contract. | Indexed |
| `naics_code` | `TEXT` | The NAICS code for the contract. | |
| `psc_code` | `TEXT` | The Product Service Code for the contract. | |
| `competition_details` | `JSONB` | Stores fields related to competition. | |
| `raw_data` | `JSONB` | The complete source record. | |
| `created_at` | `TIMESTAMP` | Timestamp of record creation. | |

---

## Table: `detections`

Stores the output of the detection algorithm—a potential SBIR transition.

| Column Name | Data Type | Description | Notes |
|---|---|---|---|
| `id` | `UUID` | Primary key for the detection. | |
| `sbir_award_id` | `UUID` | Foreign key to `sbir_awards.id`. | |
| `contract_id` | `UUID` | Foreign key to `contracts.id`. | |
| `likelihood_score`| `FLOAT` | The calculated score (0.0 to 1.0). | Indexed |
| `confidence` | `TEXT` | The confidence level ('High Confidence', 'Likely Transition'). | |
| `evidence_bundle`| `JSONB` | The auditable evidence for the detection. | |
| `detection_date` | `TIMESTAMP` | When the detection was made. | |

---

## Entity Relationships

-   A `vendors` record can have many `vendor_identifiers`.
-   A `vendors` record can have many `sbir_awards`.
-   A `vendors` record can have many `contracts`.
-   A `detections` record links one `sbir_awards` record to one `contracts` record.
