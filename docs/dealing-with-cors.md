# Dealing with CORS in Better Call Buffet

This guide explains how CORS (Cross-Origin Resource Sharing) is configured and handled in the Better Call Buffet project.

## What is CORS?

CORS (Cross-Origin Resource Sharing) is a security feature implemented by browsers that restricts web pages from making requests to a different domain than the one that served the original page. This is a crucial security measure to prevent malicious websites from making unauthorized requests to other domains.

## CORS Configuration in Better Call Buffet

### Backend Configuration

The FastAPI backend is configured to handle CORS through middleware. The configuration is set up in `app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Environment Variables

CORS origins are configured through environment variables. In your `.env` file or Docker environment:

```env
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

For production, you would update this to include your production frontend domain:

```env
BACKEND_CORS_ORIGINS=["https://your-frontend-domain.com"]
```

## Common CORS Issues and Solutions

### 1. Missing CORS Headers

**Error Message:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/accounts/active' from origin 'http://localhost:3000' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**Solution:**
- Ensure CORS middleware is properly configured in `app/main.py`
- Verify that your frontend origin is included in `BACKEND_CORS_ORIGINS`
- Restart the FastAPI server after making changes

### 2. Credentials Issues

**Error Message:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/accounts/active' from origin 'http://localhost:3000' has been blocked by CORS policy: The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*' when the request's credentials mode is 'include'.
```

**Solution:**
- Set `allow_credentials=True` in CORS middleware
- Specify exact origins instead of using wildcards
- Ensure frontend requests include `credentials: 'include'` in fetch/axios configuration

### 3. Preflight Request Failures

**Error Message:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/accounts/active' from origin 'http://localhost:3000' has been blocked by CORS policy: Response to preflight request doesn't pass access control check: No 'Access-Control-Allow-Methods' header is present on the response.
```

**Solution:**
- Ensure `allow_methods=["*"]` is set in CORS middleware
- Add specific methods if needed: `allow_methods=["GET", "POST", "PUT", "DELETE"]`

## Frontend Configuration

### Using Fetch

```javascript
fetch('http://localhost:8000/api/v1/accounts/active', {
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json',
  },
})
```

### Using Axios

```javascript
axios.defaults.withCredentials = true;
axios.get('http://localhost:8000/api/v1/accounts/active');
```

## Testing CORS Configuration

1. Start your backend server:
```bash
poetry run uvicorn app.main:app --reload
```

2. Start your frontend development server:
```bash
npm start  # or yarn start
```

3. Open browser developer tools (F12)
4. Check the Network tab for CORS-related errors
5. Verify that requests include the correct CORS headers

## Production Considerations

1. **Security**: Only allow necessary origins in production
2. **Environment Variables**: Use different CORS configurations for development and production
3. **Monitoring**: Set up logging for CORS-related issues
4. **Documentation**: Keep this guide updated with any changes to CORS configuration

## Troubleshooting Checklist

- [ ] CORS middleware is properly configured in `app/main.py`
- [ ] Frontend origin is included in `BACKEND_CORS_ORIGINS`
- [ ] Server has been restarted after configuration changes
- [ ] Frontend requests include proper credentials configuration
- [ ] Network requests show correct CORS headers in browser dev tools
- [ ] Environment variables are properly loaded

## Additional Resources

- [MDN Web Docs: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [Browser Security: Same-Origin Policy](https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy) 