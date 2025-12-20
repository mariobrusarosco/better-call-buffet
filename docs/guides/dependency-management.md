# Dependency Management Guide

## Philosophy

**Our dependency strategy balances stability with security:**
- **Critical dependencies** (auth, database, config) → Exact pins or strict ranges
- **Framework dependencies** (FastAPI, logging) → Allow minor updates (caret `^`)
- **Security libraries** → Allow patches, review before major updates
- **Always test critical paths** (login, database) after ANY dependency change

## Version Pinning Strategies

### Exact Pin (`package = "1.2.3"`)
**When to use:** Dependencies where minor version changes break compatibility

**Examples:**
```toml
sqlalchemy = "2.0.27"       # ORM - breaking changes between minors
pydantic = "2.9.2"          # Breaking changes in 2.x minors
passlib = "1.7.4"           # Auth library - never auto-update
```

**Upgrade process:** Manual testing required, coordinate with team

---

### Strict Range (`package = ">=1.0.0,<2.0.0"`)
**When to use:** Transitive dependencies with known compatibility issues

**Examples:**
```toml
bcrypt = ">=3.1.0,<4.0.0"   # MUST stay on 3.x for passlib
```

**Upgrade process:** Check compatibility matrix before upgrading

---

### Caret (`package = "^1.2.3"`)
**When to use:** Stable libraries following semantic versioning
- Allows: `1.2.3` → `1.9.9` ✅
- Blocks: `1.2.3` → `2.0.0` ❌

**Examples:**
```toml
fastapi = "^0.125.0"        # Stable API, safe minor updates
alembic = "^1.15.2"         # Safe within major version
pyjwt = "^2.10.1"           # Follows semver
```

**Upgrade process:** Review changelog, test before production

---

## Critical Dependency Categories

### 🔴 NEVER Auto-Update (Exact Pins)

```toml
# Authentication - breaks login if wrong version
passlib = "1.7.4"
bcrypt = ">=3.1.0,<4.0.0"

# Database - breaks queries/migrations
sqlalchemy = "2.0.27"
psycopg2-binary = "2.9.9"

# Configuration - breaks app startup
pydantic = "2.9.2"
pydantic-settings = "2.2.1"
```

**Why:** These libraries have breaking changes in minor versions or known incompatibilities.

**Update checklist:**
1. ✅ Read FULL changelog
2. ✅ Test in Docker locally
3. ✅ Test critical paths: login, database queries, config loading
4. ✅ Run full test suite
5. ✅ Update in separate PR with rollback plan

---

### 🟡 Review Before Update (Caret OK)

```toml
# Web framework - test API endpoints
fastapi = "^0.125.0"

# PDF parsing - can break parsing logic
pdfplumber = "^0.11.0"

# Migrations - test against dev database
alembic = "^1.15.2"
```

**Why:** Generally stable but can introduce bugs in edge cases.

**Update checklist:**
1. ✅ Check release notes
2. ✅ Test affected features
3. ✅ Monitor Sentry after deployment

---

### 🟢 Safe to Update (Caret OK)

```toml
# Logging - worst case: log format changes
structlog = "^25.4.0"
sentry-sdk = "^2.0.0"

# AI - isolated feature
openai = "^1.0.0"
httpx = "^0.25.0"
```

**Why:** Isolated features, easy to rollback, minimal impact.

**Update checklist:**
1. ✅ Review changelog
2. ✅ Deploy to production

---

## Upgrade Commands Reference

### ❌ NEVER Use These (Too Dangerous)

```bash
# Updates ALL dependencies (breaks everything)
poetry update

# Updates with ALL transitive dependencies
poetry update <package>
```

**Why dangerous:** Can upgrade bcrypt, pydantic, sqlalchemy in background → breaks auth/database.

---

### ✅ Safe Upgrade Methods

**Method 1: Add specific version (safest)**
```bash
# Explicit version upgrade
docker compose exec web poetry add "fastapi@0.125.0"
docker compose exec web poetry add "starlette@0.50.0"
```

**Method 2: Update lock file only**
```bash
# Regenerate lock without changing versions
docker compose exec web poetry lock --no-update

# After manual pyproject.toml edit
docker compose exec web poetry lock
docker compose exec web poetry install
```

**Method 3: Check outdated packages**
```bash
# See what's outdated
docker compose exec web poetry show --outdated

# Then decide which to update manually
```

---

## Common Compatibility Issues

### passlib + bcrypt
**Problem:** passlib 1.7.4 requires bcrypt 3.x (not 4.x+)

**Solution:**
```toml
passlib = "1.7.4"
bcrypt = ">=3.1.0,<4.0.0"  # Pin to 3.x
```

**Error if wrong:**
```
AttributeError: module 'bcrypt' has no attribute '__about__'
```

---

### pydantic + pydantic-settings
**Problem:** Version mismatch causes Settings validation errors

**Solution:**
```toml
pydantic = "2.9.2"          # Must match
pydantic-settings = "2.2.1" # Must match
```

**Error if wrong:**
```
ValidationError: 16 validation errors for Settings
```

---

### FastAPI + starlette
**Problem:** FastAPI pins starlette to specific range

**Solution:** Let FastAPI manage starlette, don't pin it directly
```toml
fastapi = "^0.125.0"  # Manages starlette internally
# No explicit starlette pin
```

**Check compatibility:**
```bash
docker compose exec web poetry show fastapi
# Look at "dependencies" section for starlette range
```

---

## Emergency Rollback Procedure

If dependency upgrade breaks production:

### Option 1: Revert Commit
```bash
git revert HEAD
git push origin main
# Railway auto-deploys fixed version
```

### Option 2: Pin to Previous Version
```bash
# In pyproject.toml
fastapi = "0.124.0"  # Downgrade

docker compose exec web poetry lock
docker compose exec web poetry install
git commit -am "fix: rollback fastapi to 0.124.0"
git push
```

### Option 3: Railway Rollback
```bash
# Via Railway dashboard
# Deployments → Select previous working deployment → Redeploy
```

---

## Pre-Deployment Checklist

Before merging dependency updates:

- [ ] ✅ Read FULL changelog for ALL updated packages
- [ ] ✅ Check transitive dependencies: `poetry show <package>`
- [ ] ✅ Test critical paths locally in Docker:
  - [ ] Login (POST /api/v1/auth/login)
  - [ ] Database queries (GET /api/v1/users)
  - [ ] Config loading (GET /health)
  - [ ] Migrations (alembic check)
- [ ] ✅ Run security audit: `poetry run pip-audit`
- [ ] ✅ Run full test suite: `poetry run pytest`
- [ ] ✅ CI passes in GitHub Actions
- [ ] ✅ Have rollback plan ready

---

## Poetry Version Synchronization

**Critical:** Poetry version MUST match across environments

**Current version:** `2.2.1`

**Where to update:**
1. Local: `poetry self update 2.2.1`
2. Docker: `Dockerfile` line ~15
3. CI: `.github/workflows/deploy.yml` line ~40

**Check versions:**
```bash
# Local
poetry --version

# Docker
docker compose exec web poetry --version
```

**Why critical:** Different Poetry versions generate incompatible `poetry.lock` files.

---

## Dependency Audit Schedule

**Weekly:**
- [ ] Check for security advisories: `poetry run pip-audit`
- [ ] Fix critical vulnerabilities (CVSS 7.0+)

**Monthly:**
- [ ] Review outdated packages: `poetry show --outdated`
- [ ] Update non-critical dependencies (logging, monitoring)
- [ ] Test in staging environment

**Quarterly:**
- [ ] Plan major version upgrades (FastAPI, SQLAlchemy)
- [ ] Coordinate with team
- [ ] Schedule maintenance window

---

## Getting Help

**Before asking Claude Code to update dependencies:**

1. Specify exactly which package and why
2. Mention if it's a security fix or feature need
3. Ask for compatibility check first

**Example:**
```
"I need to update starlette to fix CVE-2025-62727.
Can you check if FastAPI 0.125.0 supports starlette 0.50.0?
If yes, show me the safe upgrade steps."
```

**What NOT to say:**
```
"Update all dependencies"  # Too dangerous
"Fix the vulnerabilities"  # Too vague
```

---

## Resources

- [Poetry Dependency Specification](https://python-poetry.org/docs/dependency-specification/)
- [Semantic Versioning](https://semver.org/)
- [FastAPI Release Notes](https://fastapi.tiangolo.com/release-notes/)
- [SQLAlchemy Changelog](https://docs.sqlalchemy.org/en/20/changelog/)
- [Pydantic Migration Guide](https://docs.pydantic.dev/latest/migration/)
