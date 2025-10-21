# Quickstart: SBIR Transition Detection

**Feature**: Detect Untagged SBIR Phase III Transitions
**Date**: 2025-10-15

This guide provides instructions to set up and run the SBIR Transition Detection service.

## Prerequisites

- Docker
- Docker Compose
- `curl` or a similar HTTP client

## Setup and Running the Service

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd sbir-transition-classifier
    ```

2.  **Switch to the feature branch**:
    ```bash
    git checkout 001-prompt-detect-untagged
    ```

3.  **Build and start the services**:
    The project is containerized using Docker. The `docker-compose.yml` file defines the API service and the PostgreSQL database.

    ```bash
    docker-compose up --build -d
    ```
    This command will build the Docker images and start the containers in detached mode.

## Using the API

The API will be available at `http://localhost:8000`.

### 1. Ingest Data (Manual Step for Now)

For the initial version, data ingestion is a manual process. The `data/award_data.csv` file must be present. For contract data, you will need to download the bulk data from USAspending.gov and place it in the `data/` directory. A script will be provided to load this data into the database.

```bash
# (Example of a future command)
docker-compose exec api python -m scripts.load_bulk_data --year 2022
```

### 2. Trigger an Analysis

To start detecting transitions for a specific vendor, send a `POST` request to the `/detect` endpoint.

```bash
cURL -X POST http://localhost:8000/detect \
-H "Content-Type: application/json" \
-d '{
  "vendor_identifier": "ABCDE12345"
}'
```

The API will respond with a task ID:

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

### 3. Retrieve Evidence

Once the analysis is complete, you can retrieve the results for a specific detection using its ID. (Note: A separate endpoint to check task status and get detection IDs would be added).

```bash
cURL http://localhost:8000/evidence/<detection-uuid>
```

The API will return the full evidence bundle for the detection:

```json
{
  "detection_id": "<detection-uuid>",
  "likelihood_score": 0.85,
  "confidence": "High Confidence",
  "reason_string": "Sole-source IDV awarded 8 months after Phase II completion by the same agency.",
  "source_sbir_award": {
    "piid": "W911NF-18-C-0033",
    "agency": "DEPT OF DEFENSE",
    "completion_date": "2020-01-15"
  },
  "source_contract": {
    "piid": "HD0340-20-D-0001",
    "agency": "DEPT OF DEFENSE",
    "start_date": "2020-09-01",
    "competition": {}
  }
}
```
