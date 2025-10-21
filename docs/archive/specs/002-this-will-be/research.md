# Research: Local Analyst Configuration Mode

**Date**: 2025-10-15  
**Feature**: Local execution with YAML configuration  
**Status**: Complete

## Research Tasks

### 1. YAML Configuration Management in Python

**Decision**: Use PyYAML with Pydantic for validation  
**Rationale**: PyYAML provides robust parsing, Pydantic ensures type safety and validation with clear error messages  
**Alternatives considered**: 
- Pure PyYAML: Lacks validation
- TOML: Less familiar to analysts
- JSON: Not human-readable for complex configurations

### 2. Local CLI Execution Patterns

**Decision**: Click-based CLI with subcommands  
**Rationale**: Click integrates well with existing FastAPI patterns, provides automatic help generation, and supports complex parameter validation  
**Alternatives considered**:
- argparse: More verbose, less integration with existing stack
- Typer: Good but adds dependency when Click suffices

### 3. Offline Data Processing Architecture

**Decision**: Maintain existing SQLite + Pandas pipeline, add configuration injection points  
**Rationale**: Existing architecture already supports local execution, just needs configuration parameterization  
**Alternatives considered**:
- Complete rewrite: Unnecessary complexity
- File-based processing only: Loses existing SQL optimization benefits

### 4. Configuration Validation Strategy

**Decision**: Schema-first validation with runtime checks  
**Rationale**: Catch configuration errors early with specific guidance on valid ranges and formats  
**Alternatives considered**:
- Runtime-only validation: Poor user experience
- No validation: Risk of silent failures

### 5. Local Setup and Distribution

**Decision**: Poetry + Docker Compose for development, standalone script for production  
**Rationale**: Maintains existing development workflow while providing simple deployment option  
**Alternatives considered**:
- Docker-only: Adds complexity for simple local use
- pip-only: Dependency management challenges

## Implementation Patterns

### Configuration Structure
```yaml
detection:
  thresholds:
    high_confidence: 0.85
    likely_transition: 0.65
  weights:
    sole_source_bonus: 0.2
    timing_weight: 0.15
  features:
    enable_cross_service: true
    enable_text_analysis: false
  timing:
    max_months_after_phase2: 24
```

### CLI Interface
```bash
sbir-detect run --config config/custom.yaml --output results/
sbir-detect validate-config --config config/custom.yaml
sbir-detect reset-config --output config/default.yaml
```

### Error Handling
- YAML syntax errors: Line-specific guidance
- Value range errors: Show acceptable ranges
- Missing files: Point to setup documentation
