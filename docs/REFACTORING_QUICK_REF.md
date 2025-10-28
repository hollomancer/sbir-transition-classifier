# SBIR Transition Classifier - Refactoring Quick Reference

**One-page guide for developers implementing refactoring changes**

---

## 📋 Phase 1 Checklist (22-30 hours)

### Task 1: Merge Configuration Systems (4-6h)
- [ ] Add `DatabaseConfig` to `config/schema.py`
- [ ] Create `db/config.py` with loader functions
- [ ] Update `db/database.py` to use unified config
- [ ] Add database section to `config/default.yaml`
- [ ] Deprecate `core/config.py` with warnings
- [ ] Update `AGENTS.md` documentation
- [ ] **Test:** `poetry run pytest tests/unit/test_config_and_detection.py`

### Task 2: Consolidate CLI (6-8h)
- [ ] Create `cli/data.py` (from `scripts/load_bulk_data.py`)
- [ ] Create `cli/export.py` (from `scripts/export_data.py`)
- [ ] Create `cli/analysis.py` (from `scripts/enhanced_analysis.py`)
- [ ] Create `cli/db.py` (from `scripts/setup_local_db.py`)
- [ ] Update `cli/main.py` to register new commands
- [ ] Add deprecation warnings to old scripts
- [ ] Update README.md with new command patterns
- [ ] **Test:** `poetry run sbir-detect --help`

### Task 3: Expand Tests (12-16h)
- [ ] Create `tests/conftest.py` with shared fixtures
- [ ] Create `tests/unit/config/test_loader.py`
- [ ] Create `tests/unit/config/test_schema.py`
- [ ] Create `tests/unit/ingestion/test_sbir_ingester.py`
- [ ] Create `tests/unit/ingestion/test_contract_ingester.py`
- [ ] Create `tests/unit/detection/test_scoring.py`
- [ ] Create `tests/unit/detection/test_pipeline.py`
- [ ] Add pytest config to `pyproject.toml`
- [ ] **Test:** `poetry run pytest --cov --cov-report=term`
- [ ] **Goal:** 50%+ coverage

---

## 🔧 Key Code Changes

### Before & After: Configuration

```python
# ❌ OLD (core/config.py)
from sbir_transition_classifier.core.config import settings
db_url = settings.DATABASE_URL

# ✅ NEW (unified config)
from sbir_transition_classifier.db.config import get_database_config
db_config = get_database_config()
db_url = db_config.url
```

### Before & After: CLI Invocation

```bash
# ❌ OLD (multiple patterns)
poetry run python -m scripts.load_bulk_data load-sbir-data --file-path data/awards.csv
poetry run python -m sbir_transition_classifier.scripts.export_data export-jsonl

# ✅ NEW (unified CLI)
poetry run sbir-detect data load-sbir --file-path data/awards.csv
poetry run sbir-detect export jsonl --output-path output/results.jsonl
```

### Before & After: Session Management

```python
# ❌ OLD (manual cleanup)
db = SessionLocal()
try:
    results = db.query(models.Detection).all()
finally:
    db.close()

# ✅ NEW (context manager)
from sbir_transition_classifier.db.session import get_db_session

with get_db_session() as db:
    results = db.query(models.Detection).all()
```

---

## 📁 New File Structure

```
src/sbir_transition_classifier/
├── cli/
│   ├── main.py          # Entry point
│   ├── data.py          # ✨ NEW: Data loading commands
│   ├── export.py        # ✨ NEW: Export commands
│   ├── analysis.py      # ✨ NEW: Analysis commands
│   └── db.py            # ✨ NEW: Database management
├── config/
│   └── schema.py        # ✨ UPDATED: Added DatabaseConfig
├── db/
│   ├── database.py      # ✨ UPDATED: Uses unified config
│   ├── config.py        # ✨ NEW: Config loader
│   └── session.py       # ✨ NEW: Session helpers
└── core/
    └── config.py        # ⚠️ DEPRECATED

tests/
├── conftest.py          # ✨ NEW: Shared fixtures
├── unit/
│   ├── config/          # ✨ NEW: Config tests
│   ├── ingestion/       # ✨ NEW: Ingestion tests
│   └── detection/       # ✨ NEW: Detection tests
└── integration/         # Existing

scripts/                 # ⚠️ DEPRECATED (add warnings)
```

---

## 🚀 Quick Commands

### Start Refactoring
```bash
git checkout -b refactor/consolidation-phase-1
git branch backup/pre-refactor-$(date +%Y%m%d)
```

### Run Tests
```bash
# Unit tests only
poetry run pytest tests/unit/ -v

# With coverage
poetry run pytest --cov --cov-report=html

# Specific test file
poetry run pytest tests/unit/config/test_loader.py -v
```

### Check Progress
```bash
# Test coverage
poetry run coverage report

# Line count
wc -l src/sbir_transition_classifier/**/*.py | tail -1

# Find old imports
grep -r "from.*core.config import settings" src/
```

### Verify Changes
```bash
# All CLI commands accessible
poetry run sbir-detect --help

# Config loads correctly
poetry run sbir-detect config validate --config config/default.yaml

# Database connects
poetry run sbir-detect quick-stats
```

---

## ⚠️ Common Pitfalls

1. **Don't remove old code immediately** - Deprecate first
2. **Update imports everywhere** - Search for old patterns
3. **Test after each task** - Don't accumulate changes
4. **Keep commits small** - One logical change per commit
5. **Update docs as you go** - Don't defer to end

---

## 🎯 Success Metrics

| Metric | Target | Check Command |
|--------|--------|---------------|
| Test Coverage | 50%+ | `poetry run coverage report` |
| No Import Errors | 0 | `poetry run python -c "import sbir_transition_classifier"` |
| All Tests Pass | 100% | `poetry run pytest` |
| CLI Works | Yes | `poetry run sbir-detect --help` |
| Docs Updated | Yes | Manual review |

---

## 🔄 Rollback Plan

```bash
# Reset specific file
git checkout HEAD~1 -- path/to/file.py

# Reset entire feature branch
git checkout backup/pre-refactor-YYYYMMDD

# Abandon changes
git checkout main
git branch -D refactor/consolidation-phase-1
```

---

## 📚 Documentation Map

- **This Document** - Quick reference
- **REFACTORING_OPPORTUNITIES.md** - Full analysis (777 lines)
- **REFACTORING_GUIDE.md** - Step-by-step instructions (1,120 lines)
- **REFACTORING_SUMMARY.md** - Executive summary (311 lines)
- **AGENTS.md** - Coding guidelines

---

## 💡 Pro Tips

1. **Use search & replace** - Update imports in bulk
2. **Run tests frequently** - Catch issues early
3. **Commit often** - Easy to rollback small changes
4. **Update one module at a time** - Don't mix concerns
5. **Ask for help** - Open issue if stuck

---

## 📞 Getting Help

**Stuck on something?**
1. Check REFACTORING_GUIDE.md troubleshooting section
2. Search existing issues on GitHub
3. Open new issue with `refactor` label
4. Ask in team chat/Slack

**Found a bug?**
1. Document the issue
2. Create minimal reproduction
3. File bug report
4. Continue with other tasks

---

## ✅ Final Checklist Before Merge

- [ ] All tests pass: `poetry run pytest`
- [ ] Coverage ≥50%: `poetry run coverage report`
- [ ] No lint errors: `poetry run ruff check src/`
- [ ] Docs updated: README.md, AGENTS.md
- [ ] Deprecation warnings in place
- [ ] CLI works: `poetry run sbir-detect --help`
- [ ] Example workflow runs end-to-end
- [ ] CHANGELOG.md updated
- [ ] PR description complete

---

**Ready to start? Follow REFACTORING_GUIDE.md step by step!**