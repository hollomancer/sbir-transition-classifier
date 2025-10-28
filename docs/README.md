# Documentation Index

This document provides an overview of the consolidated documentation structure for the SBIR Transition Classifier project.

## Primary Documentation

### **[README.md](README.md)** - Main Project Documentation
**Status**: ✅ Current and Comprehensive
- Complete project overview, setup instructions, and usage guide
- Architecture overview and command reference
- Development workflow and contributing guidelines

### **[AGENTS.md](AGENTS.md)** - Repository Guidelines  
**Status**: ✅ Current and Authoritative
- Project structure and coding conventions
- Development, testing, and deployment guidelines
- Required reading for contributors and AI agents

## Consolidated Technical Documentation

### **[SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)** - System Design & Architecture
**Status**: ✅ Newly Consolidated
- Complete system architecture diagram and data flow
- Database schema and ingestion layer design
- Detection engine algorithms and processing pipeline
- **Replaces**: `ARCHITECTURE_DIAGRAM.md`



### **[ANALYSIS_RESULTS.md](reports/ANALYSIS_RESULTS.md)** - Business Analysis & Key Findings
**Status**: ✅ Newly Consolidated
- Dual-perspective success metrics (company vs award level)
- Key business insights and policy implications  
- System performance results and detection analytics
- **Replaces**: `DUAL_PERSPECTIVE_FINDINGS.md`, `SBIR_DATA_ANALYSIS_FINAL.md`, `SBIR_DATA_LOSS_ANALYSIS.md`

### **[DATA_README.md](DATA_README.md)** - Data Directory Guide
**Status**: ✅ Newly Consolidated
- Overview of all data directories (`data/`, `data_subset/`, `test_data/`)
- File requirements and download instructions
- Development and testing usage patterns
- **Replaces**: `data/README.md`, `data_subset/README.md`, `test_data/README.md`

### **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Comprehensive Development & Specifications Guide
**Status**: ✅ Newly Consolidated
- Quick start and setup instructions
- Development workflow and implementation phases
- Configuration management and deployment options
- Feature specifications and functional requirements
- Data model definitions and API specifications
- Performance optimizations and technical benchmarks
- Secondary features (local config, YAML export)
- **Consolidates**: Implementation tasks, development workflow, feature specs, and performance optimizations from specs/ and standalone docs


## Documentation Cleanup Summary

### **Removed Files** (60+ total files removed/consolidated):
- **24 duplicate AI assistant configs**: `.amazonq/`, `.claude/`, `.codex/` (identical content)
- **7 consolidated analysis docs**: Architecture, performance, and findings documents
- **3 data directory READMEs**: Now consolidated into single data guide
- **2 planning docs**: `GEMINI.md` (minimal content), `IMPLEMENTATION_PLAN.md` (future planning)
- **25+ spec system files**: Consolidated into IMPLEMENTATION_GUIDE.md
- **2 standalone specification docs**: SPECIFICATIONS.md and PERFORMANCE.md merged into IMPLEMENTATION_GUIDE.md

### **Files Kept As-Is**:
- `README.md` - Comprehensive main documentation  
- `AGENTS.md` - Current repository guidelines

### **New Structure Benefits**:
- **Reduced from 60+ to 7 markdown files** in docs/ directory
- **Eliminated duplication** while preserving all important information
- **Logical organization** by functional area (system, data, development)
- **Consolidated all development guidance** into a single comprehensive reference
- **Co-located specifications with implementation** for better discoverability
- **Maintained comprehensive coverage** of all technical, business, and development aspects

## Quick Reference

| Need | Document |
|------|----------|
| **Getting started** | README.md |
| **Contributing code** | AGENTS.md |  
| **Understanding the system** | SYSTEM_ARCHITECTURE.md |
| **Business insights** | [ANALYSIS_RESULTS.md](reports/ANALYSIS_RESULTS.md) |
| **Data setup** | DATA_README.md |
| **Development & specifications** | IMPLEMENTATION_GUIDE.md |
| **Testing strategy** | TESTING_STRATEGY.md |
| **Product roadmap** | ROADMAP.md |

This consolidated structure maintains all essential information while significantly improving navigation and reducing maintenance overhead.