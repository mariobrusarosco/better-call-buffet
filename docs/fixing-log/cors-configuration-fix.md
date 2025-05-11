# CORS Configuration Fix

## Issue Context
**Date**: 2024-03-19
**Error**: CORS policy blocked requests from frontend to backend
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/accounts/active' from origin 'http://localhost:3000' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## Problem
The FastAPI backend was not properly configured to handle CORS requests from the frontend application running on `http://localhost:3000`. The CORS middleware was present but the configuration was overly complex and not working as expected.

## Solution
1. Simplified the CORS configuration in `app/core/config.py`:
   - Removed unnecessary validator
   - Changed `List[AnyHttpUrl]` to `List[str]` for simpler URL handling
   - Kept the basic configuration that works with the `.env` file format

2. Environment configuration in `.env`:
```env
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

3. CORS middleware in `app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Key Learnings
1. Keep CORS configuration simple and straightforward
2. Use string-based URL lists instead of complex validators
3. Ensure proper environment variable format in `.env`
4. Restart the server after making CORS configuration changes

## Related Documentation
- [CORS Guide](../dealing-with-cors.md)
- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)

## Testing
1. Frontend running on `http://localhost:3000`
2. Backend running on `http://localhost:8000`
3. API endpoint `/api/v1/accounts/active` accessible from frontend
4. No CORS errors in browser console 