# Better Call Buffet

## 🚀 Developer Onboarding: The Golden Path for Local Development

Welcome to the Better Call Buffet project! This section will guide you through the ideal developer experience (DX) for starting, developing, and stopping the API—leveraging Docker for consistency, hot reload, and productivity.

### Why Docker?

- **Consistency:** Everyone runs the same environment—no more "works on my machine."
- **Simplicity:** One command starts everything (API + database).
- **Isolation:** No need to install Python, Poetry, or Postgres locally.
- **Production Parity:** Your local setup matches production, reducing surprises.

---

### 🏁 Prerequisites

- **Docker & Docker Compose** must be installed.
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Compose)

---

### ▶️ Quick Start Cheat Sheet

| Action         | Command                                      | What Happens?                   |
| -------------- | -------------------------------------------- | ------------------------------- |
| Start API & DB | `docker-compose up`                          | Hot reload, logs, DB all in one |
| Stop API & DB  | `Ctrl+C` or `docker-compose down`            | Clean shutdown                  |
| Run migrations | `docker-compose exec web alembic ...`        | DB schema updated               |
| Run tests      | `docker-compose exec web poetry run pytest`  | Tests run inside container      |
| Format code    | `docker-compose exec web poetry run black .` | Code formatted inside container |

---

### 🌊 Visual Workflow Diagram

```mermaid
flowchart TD
    A[Edit Code] -- Save --> B[Docker Volume Mount]
    B -- Change Detected --> C[Uvicorn in Docker]
    C -- Hot Reload --> D[API Restarts]
    D -- Logs --> E[Docker Compose Terminal]
    F[Frontend/HTTP Client] -- Request --> D
    D -- Response/Error --> F
```

---

### 🏆 Best Practices

- **Always use Docker Compose** for local development.
- **Never use `--reload` in production** (for security/performance).
- **Check logs** in your terminal for errors and debugging.
- **Use the provided commands** for migrations, testing, and formatting.

---

### 📚 Further Reading

- [Railway Deployment Guide](RAILWAY_DEPLOYMENT_GUIDE.md)

---

## The Golden Path: Standardized Development with Docker

To ensure a consistent, predictable, and productive development environment for every engineer, this project uses **Docker as the single, required standard for local development.**

### Why Docker?

- **Consistency:** Eliminates "it works on my machine" problems by ensuring everyone runs the exact same environment, from dependencies to database versions.
- **Simplicity:** Get a fully running application and database with a single command (`docker-compose up`). No need to install and configure PostgreSQL or Python locally.
- **Isolation:** Keeps your local machine clean. All project dependencies are managed inside containers and won't conflict with other projects.
- **Production Parity:** Our local setup mirrors the containerized environment used in production, reducing surprises during deployment.

---

## 🚀 **Serverless Architecture with Railway**

### **🎓 Understanding Your Production Setup**

Your Better Call Buffet application runs on **Railway's serverless platform** with automatic scaling and zero-downtime deployments - all without managing any servers!

**📚 [Railway Deployment Guide](RAILWAY_DEPLOYMENT_GUIDE.md)**

**What you get automatically:**

- ✅ **Automatic scaling** (scale to zero when not in use)
- ✅ **Zero-downtime deployments** (rolling deployments with health checks)
- ✅ **Built-in load balancing** (requests distributed intelligently)
- ✅ **Cost optimization** (pay only for what you use)
- ✅ **Simple deployment** (GitHub integration)

**Current monthly cost:** ~$0-5 (scales with usage, generous free tier)

### **🏗️ Production Architecture**

```mermaid
graph LR
    A[GitHub Push] --> B[CI/CD Pipeline]
    B --> C[Railway Platform]
    C --> D[Auto-Scaling Services]
    D --> E[Your FastAPI App]
    E --> F[Railway Postgres]
```

**Companies using similar architecture:** Many modern startups and scale-ups

### **🔄 Production Migration Process (CI/CD)**

When you push code to the `main` branch, here's exactly what happens:

```mermaid
sequenceDiagram
    participant Dev as 👨‍💻 Developer
    participant GH as 📂 GitHub
    participant GA as ⚡ GitHub Actions
    participant RB as 🏗️ Railway Builder
    participant RP as 🌍 Railway Platform
    participant DB as 🗄️ Railway Postgres

    Dev->>GH: git push origin main
    GH->>GA: Trigger workflow
    GA->>GA: Checkout code
    GA->>GA: Setup railway CLI
    
    Note over GA,RB: Build & Deploy Phase
    GA->>RB: railway up
    RB->>RB: Build Docker image
    RB->>RB: Install dependencies
    RB->>RB: Create optimized container
    
    Note over RB,RP: Migration & Release Phase
    RB->>DB: Run: alembic upgrade head
    Note right of DB: Database migrations<br/>run BEFORE deployment
    DB-->>RB: ✅ Migrations successful
    
    RB->>RP: Deploy new container
    RP->>RP: Health checks pass
    RP->>RP: Zero-downtime rollout
    
    Note over RP: App is Live! 🎉
    RP-->>Dev: Deployment complete
```

**🔒 Zero-Risk Deployment:**
1. **Database migrations run first** - if they fail, deployment stops
2. **Health checks** ensure your app starts correctly
3. **Rolling deployment** - old version stays live until new one is ready
4. **Automatic rollback** if anything goes wrong

**⏱️ Timeline:** ~2-3 minutes from push to live

### **🎯 Professional Deployment Flow**

Your Better Call Buffet project now includes a complete professional deployment system with monitoring, health checks, and automated notifications.

#### **🔄 Deployment Options**

```mermaid
graph TD
    A[Code Changes] --> B{Deployment Method}
    B -->|Automatic| C[Push to main branch]
    B -->|Manual| D[./scripts/deploy-monitor.sh]
    
    C --> E[GitHub Actions]
    D --> F[Local Deploy Script]
    
    E --> G[Railway Deployment]
    F --> G
    
    G --> H[Migration Check]
    H --> I[Database Migrations]
    I --> J[Health Checks]
    J --> K[Success Notifications]
    
    K --> L[🎉 Live Production App]
```

#### **📊 Deployment Monitoring Dashboard**

```mermaid
graph LR
    subgraph "🏥 Health Monitoring"
        A[Health Endpoint] --> B[/health]
        B --> C[30 Attempts]
        C --> D[10s Intervals]
        D --> E[5min Timeout]
    end
    
    subgraph "📈 Deployment Tracking"
        F[Deploy Start] --> G[Migration Status]
        G --> H[Build Progress]
        H --> I[Health Validation]
        I --> J[Success/Failure]
    end
    
    subgraph "🔔 Notifications"
        K[🚀 Deploy Started]
        L[✅ Migration Success]
        M[🏥 Health Check Pass]
        N[🎉 Deploy Complete]
        O[❌ Deploy Failed]
    end
```

#### **🛠️ Manual Deployment Commands**

| Command | Purpose | Output |
|---------|---------|---------|
| `./scripts/deploy-monitor.sh` | Full monitored deployment | Real-time status + health checks |
| `railway up` | Basic deployment | Standard Railway output |
| `railway logs` | View live logs | Streaming application logs |
| `railway status` | Check app health | Service status + health |
| `railway shell` | Access production shell | Direct container access |

#### **🔍 Production Monitoring Tools**

```mermaid
flowchart TD
    A[Production App] --> B[Built-in Monitoring]
    A --> C[Manual Tools]
    
    B --> D[📊 Fly.io Grafana]
    B --> E[📈 Prometheus Metrics]
    B --> F[📋 Live Logs]
    
    C --> G[fly logs]
    C --> H[fly status]
    C --> I[Health Endpoint]
    
    D --> J[Performance Metrics]
    E --> K[Resource Usage]
    F --> L[Error Tracking]
```

#### **🎯 Production URLs & Endpoints**

- **🌐 Production App:** https://your-app.railway.app
- **🏥 Health Check:** https://your-app.railway.app/health
- **📖 API Docs:** https://your-app.railway.app/docs
- **📊 Railway Dashboard:** https://railway.app/dashboard

#### **🚨 Troubleshooting Guide**

```mermaid
flowchart TD
    A[Deployment Failed?] --> B{Check Error Type}
    
    B -->|Migration Error| C[fly logs --app better-call-buffet]
    B -->|Build Error| D[Check GitHub Actions]
    B -->|Health Check Failed| E[curl https://your-app.railway.app/health]
    
    C --> F[Review migration logs]
    D --> G[Fix code issues]
    E --> H[Check app startup]
    
    F --> I[Fix database schema]
    G --> J[Push new commit]
    H --> K[Check environment variables]
    
    I --> L[Redeploy]
    J --> L
    K --> L
```

**Common Issues & Solutions:**

| Issue | Command to Check | Solution |
|-------|------------------|----------|
| Migration fails | `fly ssh console -C "alembic current"` | Review migration files |
| App won't start | `fly logs` | Check startup logs |
| Health check fails | `curl https://your-app.railway.app/health` | Verify app is responding |
| Build fails | Check GitHub Actions | Fix code/dependencies |

---

## Local Development Setup

### Prerequisites

- **Docker & Docker Compose:** Must be installed on your system.
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)

### Running the Application

1.  **Clone the repository.**
2.  **Navigate to the project root directory.**
3.  **Start the services:**

    ```bash
    docker-compose up -d --build
    ```

That's it. The application stack is now running.

- **API URL:** [http://localhost:8000](http://localhost:8000)
- **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database:** A PostgreSQL instance is running and exposed on `localhost:5432`. You can connect to it with the credentials in `docker-compose.yml`.

### Stopping the Application

To stop the running containers, execute:

```bash
docker-compose down
```

---

## Common Development Tasks

All commands should be executed from your host machine's terminal in the project root.

### Working with Database Migrations

As you develop new features, you will often need to modify the database schema. This is handled by `Alembic`. Here are the essential commands for your daily work.

**Applying Migrations**

To apply all outstanding migrations and bring the database up to the latest version, run:

```bash
docker-compose exec web alembic upgrade head
```

**Creating a New Migration**

After you have changed your SQLAlchemy models (e.g., in `app/domains/.../models.py`), you need to generate a new migration script. Alembic can often detect these changes automatically.

```bash
docker-compose exec web alembic revision --autogenerate -m "A short, descriptive message about your changes"
```

- `--autogenerate`: Tells Alembic to compare your models to the current database state and generate the migration code.
- `-m "..."`: Provides a message that will become part of the migration file name. Always use a descriptive message!

After running this, a new migration file will appear in the `migrations/versions/` directory. You should always inspect this file to ensure it's correct before committing it.

**Checking the Current Status**

To see the current revision of your database, use:

```bash
docker-compose exec web alembic current
```

This is useful to confirm that your migrations have been applied correctly.

### Running Tests

Execute the `pytest` suite inside the `web` container:

```bash
docker-compose exec web poetry run pytest
```

### Code Formatting & Linting

Run the formatters and linters inside the `web` container:

```bash
# Run Black for formatting
docker-compose exec web poetry run black .
```

---

## Project Structure

```
better-call-buffet/
├── app/
│ ├── api/ # API endpoints
│ ├── core/ # Core functionality
│ ├── db/ # Database models and config
│ └── domains/ # Business logic domains
├── docs/ # Documentation
├── migrations/ # Alembic database migrations
└── docker-compose.yml # Defines the local development environment
```

## Contributing

1. Create a feature branch.
2. Make your changes inside the containerized environment.
3. Run tests: `docker-compose exec web poetry run pytest`
4. Format code: `docker-compose exec web poetry run black .`
5. Submit a pull request.

## CI/CD Pipeline

This project uses an automated CI/CD pipeline powered by GitHub Actions. The pipeline includes:

- **Code Quality Checks**: Automated linting, formatting, and type checking.
- **Security Scanning**: Dependency vulnerability detection.
- **Docker Build**: Containerized application building and testing.
- **Automated Deployment**: Production deployment to Railway.

### 📚 Documentation

- **[Railway Deployment Guide](RAILWAY_DEPLOYMENT_GUIDE.md)** - Complete guide to deploying on Railway.

---

## Architecture

```
┌─────────────────────────────────────┐
│  🌐 ROUTER LAYER (HTTP Concerns)     │
│  - Request/Response formatting       │
│  - HTTP status codes                 │
│  - Pydantic validation               │
│  - API versioning                    │
└─────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────┐
│  💼 SERVICE LAYER (Business Logic)   │
│  - Domain operations                 │
│  - Business rules                    │
│  - Data validation                   │
│  - Returns domain models             │
└─────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────┐
│  🗄️ DATA LAYER (Persistence)        │
│  - Database queries                  │
│  - SQLAlchemy models                 │
│  - Transaction management            │
└─────────────────────────────────────┘
```

## 📚 Documentation

### Core Development Guides

- **[Railway Deployment Guide](RAILWAY_DEPLOYMENT_GUIDE.md)** - Complete guide to deploying on Railway

## License

[License details here]
