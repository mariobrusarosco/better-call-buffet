# Railway Environment Variables Configuration

## Required Environment Variables

### Database

- `DATABASE_URL` - PostgreSQL connection string (automatically provided by Railway PostgreSQL service)

### Security

- `SECRET_KEY` - Application secret key for JWT tokens and encryption
- `SENTRY_DSN` - Sentry error tracking DSN (optional but recommended for production)

### CORS

- `BACKEND_CORS_ORIGINS` - JSON array of allowed CORS origins, e.g., `["https://yourdomain.com", ""]`

### Environment

- `ENVIRONMENT` - Set to "production" for production deployment
- `DEBUG` - Set to "false" for production

### Optional

- `ENABLE_PERFORMANCE_LOGGING` - Set to "true" to enable detailed performance logs

## Railway-Specific Notes

1. **DATABASE_URL**: Railway will automatically provide this when you add a PostgreSQL service
2. **PORT**: Railway automatically sets this - no need to configure
3. **CORS Origins**: Update with your actual frontend domain(s)

## Sample Production Values

```
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secure-secret-key-here
BACKEND_CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]
SENTRY_DSN=https://your-sentry-dsn-here
ENABLE_PERFORMANCE_LOGGING=true
```
