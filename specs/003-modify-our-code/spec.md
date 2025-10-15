# Feature Specification: Migrate Export Format from JSONL to YAML

**Feature Branch**: `003-modify-our-code`  
**Created**: 2025-10-15  
**Status**: Draft  
**Input**: User description: "Modify our code base to use YAML not JSONL"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export Detection Results as YAML (Priority: P1)

Users need to export SBIR transition detection results in YAML format instead of JSONL for better human readability and easier integration with configuration management tools.

**Why this priority**: YAML is more human-readable than JSONL and integrates better with many DevOps and configuration management workflows. This is the core functionality that delivers immediate value.

**Independent Test**: Can be fully tested by running the export command and verifying YAML output format is valid and contains all detection data.

**Acceptance Scenarios**:

1. **Given** detection results exist in the database, **When** user runs export command, **Then** system generates valid YAML file with all detection data
2. **Given** no detection results exist, **When** user runs export command, **Then** system generates empty YAML file with proper structure
3. **Given** large dataset with 1000+ detections, **When** user exports to YAML, **Then** file is generated successfully without memory issues

---

### User Story 2 - Maintain Backward Compatibility (Priority: P2)

Existing users and scripts that depend on JSONL format should continue to work during the transition period.

**Why this priority**: Ensures smooth migration without breaking existing workflows and integrations.

**Independent Test**: Can be tested by running existing JSONL export commands and verifying they still produce valid JSONL output.

**Acceptance Scenarios**:

1. **Given** user specifies JSONL format explicitly, **When** export runs, **Then** system generates JSONL output as before
2. **Given** user runs legacy export commands, **When** export completes, **Then** existing scripts continue to work unchanged

---

### User Story 3 - Configure Default Export Format (Priority: P3)

System administrators need to configure the default export format (YAML or JSONL) for their organization's preferences.

**Why this priority**: Provides flexibility for different organizational needs while maintaining consistency within each deployment.

**Independent Test**: Can be tested by changing configuration and verifying new exports use the configured default format.

**Acceptance Scenarios**:

1. **Given** default format is set to YAML, **When** user runs export without format specification, **Then** system generates YAML output
2. **Given** configuration is updated to JSONL, **When** system restarts, **Then** new default takes effect for subsequent exports

---

### Edge Cases

- What happens when YAML serialization fails due to complex nested data structures?
- How does system handle very large datasets that might exceed YAML parser limits?
- What occurs when user specifies invalid format options?
- How does system behave when output directory is read-only or disk space is insufficient?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST export detection results in valid YAML format by default
- **FR-002**: System MUST maintain JSONL export capability for backward compatibility
- **FR-003**: Users MUST be able to specify output format via command-line flag (--format yaml|jsonl)
- **FR-004**: System MUST preserve all existing data fields when converting from JSONL to YAML
- **FR-005**: System MUST validate YAML output for syntax correctness before writing to file
- **FR-006**: System MUST handle large datasets (10,000+ records) without memory overflow
- **FR-007**: System MUST provide clear error messages when export format is unsupported
- **FR-008**: System MUST update CLI help documentation to reflect new YAML default
- **FR-009**: System MUST maintain existing file naming conventions with appropriate extensions (.yaml/.yml vs .jsonl)
- **FR-010**: Configuration system MUST allow setting default export format via environment variable or config file

### Key Entities

- **Detection Export**: Contains detection results, evidence bundles, vendor information, and metadata in structured format
- **Export Configuration**: Defines default format, file naming patterns, and output directory settings
- **Format Converter**: Handles transformation between JSONL and YAML representations while preserving data integrity

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing detection data exports successfully to valid YAML format without data loss
- **SC-002**: YAML export performance is within 20% of current JSONL export time for equivalent datasets
- **SC-003**: 100% of existing JSONL export functionality remains available through compatibility mode
- **SC-004**: YAML files are human-readable and 50% smaller in line count compared to equivalent JSONL
- **SC-005**: System handles datasets up to 50,000 detection records without memory issues
- **SC-006**: Zero breaking changes to existing CLI commands and their output when JSONL format is explicitly specified

## Assumptions *(mandatory)*

- Current JSONL export functionality is working correctly and will serve as the baseline for data integrity validation
- YAML format will be used for human readability, not for high-performance data processing scenarios
- Existing detection data structure is compatible with YAML serialization (no circular references or unsupported data types)
- Users have basic familiarity with YAML format or can adapt to it
- File system supports both .jsonl and .yaml/.yml file extensions
- Python PyYAML library (or equivalent) is acceptable for YAML processing

## Dependencies *(mandatory)*

- YAML parsing/serialization library (e.g., PyYAML, ruamel.yaml)
- Existing export infrastructure and CLI framework
- Current detection data models and database schema
- Configuration management system for default format settings

## Scope *(mandatory)*

### In Scope

- Modify export commands to output YAML by default
- Add format selection option (--format yaml|jsonl)
- Update CLI help and documentation
- Maintain full backward compatibility for JSONL
- Add configuration option for default format
- Validate YAML output correctness
- Handle error cases gracefully

### Out of Scope

- Modifying import/input functionality (still accepts existing data formats)
- Changing internal data storage format (database remains unchanged)
- Converting existing stored JSONL files to YAML
- Adding other export formats (XML, CSV summary remains separate)
- Modifying detection algorithms or scoring logic
- Changing database schema or data models
