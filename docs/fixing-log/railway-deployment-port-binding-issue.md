# Railway Deployment Port Binding Issue - Fix Log

**Date:** 2025-08-03  
**Issue:** FastAPI + Alembic + Docker + Poetry + Railway deployment failing with 502 errors
**Status:** ✅ RESOLVED

## Problem Summary

Railway deployment was failing with "Application failed to respond" and 502 Bad Gateway errors despite the container appearing to start successfully. The application logs showed it was running but HTTP requests were not reaching the FastAPI application.

## Root Cause Analysis

The issue was **port binding incompatibility** between our custom Dockerfile approach and Railway's expected configuration:

1. **Complex Poetry Setup**: Our Dockerfile used Poetry with virtual environments in containers
2. **Manual PORT Handling**: We tried to manually handle the PORT environment variable with `--bind 0.0.0.0:$PORT`
3. **Health Check Mismatch**: Health check was hardcoded to port 8000 while app ran on Railway's assigned port
4. **Over-Engineering**: Used complex multi-stage builds instead of Railway's recommended simple approach

## Error Symptoms

- ✅ Container built successfully
- ✅ Alembic migrations ran successfully  
- ✅ Application appeared to start (logs showed "Running on http://0.0.0.0:8080")
- ❌ HTTP requests returned 502 Bad Gateway
- ❌ Health checks failed
- ❌ All endpoints unreachable

## Failed Solution Attempts

### 1. Poetry Configuration Changes
```dockerfile
# Tried various Poetry virtual environment settings
ENV POETRY_VENV_IN_PROJECT=1  # Failed
ENV POETRY_VENV_IN_PROJECT=0  # Failed
```

### 2. Manual PORT Variable Management
```dockerfile
# Tried manual PORT handling
CMD ["hypercorn", "app.main:app", "--bind", "0.0.0.0:${PORT:-8000}"]  # Failed
```

### 3. Virtual Environment Activation
```dockerfile
# Tried direct venv activation
CMD ["bash", "-c", "source .venv/bin/activate && alembic upgrade head && hypercorn app.main:app --bind 0.0.0.0:$PORT"]  # Failed
```

## Successful Solution

### Railway's Recommended Approach
Switched to Railway's official FastAPI Dockerfile pattern from their documentation:

```dockerfile
# Use the Python 3.11 alpine official image
FROM python:3.11-alpine

# Install system dependencies needed for some Python packages
RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev curl

# Create and change to the app directory
WORKDIR /app

# Copy requirements and install dependencies first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy local code to the container image
COPY . .

# Run migrations then start the web service
CMD ["sh", "-c", "alembic upgrade head && hypercorn app.main:app --bind ::"]
```

### Key Changes That Fixed It

1. **Simplified to pip + requirements.txt**: Removed Poetry complexity from container
2. **Used `--bind ::` instead of PORT handling**: Let Railway handle port mapping automatically
3. **Alpine image**: Smaller, faster, Railway-optimized
4. **Removed custom health checks**: Let Railway handle health detection

### Requirements.txt Generation
```bash
# Added Poetry export plugin for Poetry 2.x
poetry self add poetry-plugin-export
poetry export -f requirements.txt --output requirements.txt --without-hashes --only=main
```

## Technical Insights

### Why `--bind ::` Works
- `::` binds to all interfaces (IPv4 and IPv6)
- Railway automatically maps external traffic to the container's port
- No need to manually handle PORT environment variable
- Railway's load balancer handles the routing

### Poetry vs pip in Containers
- **Poetry**: Great for development, complex in containers
- **pip**: Simple, reliable, Railway-optimized
- **Best Practice**: Use Poetry locally, pip in production containers

### Railway Port Binding Expectations
- Railway provides PORT environment variable automatically
- Apps should bind to `0.0.0.0:$PORT` OR use `::` for auto-binding
- Railway's load balancer routes traffic based on the container's listening port

## Lessons Learned

### 1. Follow Platform Conventions
- Railway has specific patterns that work best
- Don't over-engineer when simple solutions exist
- Check official platform documentation first

### 2. Container Simplicity Principle
- Containers should do one thing well
- Avoid complex dependency management in production containers
- Use the simplest working solution

### 3. Port Binding Best Practices
- Let the platform handle port mapping when possible
- Use `::` binding for platform-agnostic deployments
- Don't hardcode ports in health checks

### 4. Debugging Strategy
- Start with platform examples that work
- Simplify progressively until you find the issue
- Health checks and port binding are common failure points

## Prevention for Future

1. **Always start with platform examples** before customizing
2. **Test deployments incrementally** - don't change everything at once
3. **Use pip in containers** even if using Poetry locally
4. **Let platforms handle port binding** automatically when possible

## Stack Information

- **FastAPI**: 0.116.1
- **Alembic**: 1.15.2
- **Docker**: Alpine Python 3.11
- **Server**: Hypercorn
- **Platform**: Railway
- **Database**: Neon PostgreSQL

## Time Investment

- **Total Time**: ~3 hours of debugging
- **Issue Complexity**: Medium (port binding + platform specifics)
- **Learning Value**: High (Railway deployment patterns)

## Related Issues to Watch

- Poetry 2.x export command removal (needed plugin)
- Alpine package dependencies for PostgreSQL
- Railway automatic PORT variable handling
- Health check port mismatches in containers

---

**Resolution Date:** 2025-08-03  
**Status:** Production deployment successful ✅  
**Application URL:** https://better-call-buffet-prod-production-db41.up.railway.app/docs