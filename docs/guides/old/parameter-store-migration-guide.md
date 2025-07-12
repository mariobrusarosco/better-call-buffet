# 🔄 Parameter Store Migration Guide - Cost Optimization

## 🎓 Educational Overview

### What We're Implementing:

Migrating from **AWS Secrets Manager** to **AWS Systems Manager Parameter Store** to reduce costs while maintaining security.

### Why This Matters:

**Cost Savings**: Parameter Store is **FREE** for standard parameters (up to 10,000), while Secrets Manager costs $0.40/secret/month.

### Before vs After:

```bash
# Before: AWS Secrets Manager ($0.40/secret/month)
aws secretsmanager get-secret-value --secret-id better-call-buffet/production

# After: Parameter Store (FREE)
aws ssm get-parameter --name /better-call-buffet/DATABASE_URL --with-decryption
```

### Key Benefits:

- **💰 Cost Reduction**: Save ~$1.20/month (3 secrets × $0.40)
- **🔒 Same Security**: SecureString parameters use AWS KMS encryption
- **📈 Better Organization**: Hierarchical parameter structure
- **🚀 Faster Access**: No additional API calls for simple parameters

---

## 🚀 Migration Steps

### Step 1: Create Parameters in Parameter Store

```bash
# 1. DATABASE_URL
aws ssm put-parameter \
  --name "/better-call-buffet/DATABASE_URL" \
  --value "postgresql://username:password@your-rds-endpoint:5432/dbname" \
  --type "SecureString" \
  --description "Database connection URL for Better Call Buffet"

# 2. SECRET_KEY
aws ssm put-parameter \
  --name "/better-call-buffet/SECRET_KEY" \
  --value "your-super-secure-32-char-secret-key" \
  --type "SecureString" \
  --description "Application secret key for JWT and encryption"

# 3. CORS_ORIGINS (if needed)
aws ssm put-parameter \
  --name "/better-call-buffet/BACKEND_CORS_ORIGINS" \
  --value '["https://your-frontend-domain.com","http://localhost:3000"]' \
  --type "String" \
  --description "Allowed CORS origins"
```

### Step 2: Update IAM Permissions

Add Parameter Store permissions to your GitHub Actions role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": [
        "arn:aws:ssm:us-east-2:895583929848:parameter/better-call-buffet/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": ["arn:aws:kms:us-east-2:895583929848:key/*"],
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "ssm.us-east-2.amazonaws.com"
        }
      }
    }
  ]
}
```

### Step 3: Test Parameter Retrieval

```bash
# Test parameter access
aws ssm get-parameter \
  --name "/better-call-buffet/DATABASE_URL" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text

# Test batch retrieval
aws ssm get-parameters-by-path \
  --path "/better-call-buffet" \
  --recursive \
  --with-decryption
```

### Step 4: Deploy and Verify

1. **Deploy the updated code** (already done above)
2. **Check application logs** for successful parameter loading:
   ```
   ✅ Loaded secrets from AWS Parameter Store (Free Tier)
   ```
3. **Verify database connection** works in production

### Step 5: Clean Up Secrets Manager (Optional)

⚠️ **Only after confirming everything works!**

```bash
# List current secrets
aws secretsmanager list-secrets

# Delete old secret (saves $0.40/month)
aws secretsmanager delete-secret \
  --secret-id better-call-buffet/production \
  --force-delete-without-recovery  # Use with caution!
```

---

## 🔧 Parameter Store Best Practices

### 1. **Hierarchical Organization**

```
/better-call-buffet/
├── DATABASE_URL          (SecureString)
├── SECRET_KEY           (SecureString)
├── BACKEND_CORS_ORIGINS (String)
└── /environment/
    ├── production/
    └── staging/
```

### 2. **Parameter Types**

- **String**: Non-sensitive configuration (CORS origins, feature flags)
- **SecureString**: Sensitive data (passwords, API keys) - automatically encrypted
- **StringList**: Multiple values (comma-separated)

### 3. **Naming Conventions**

```bash
/application-name/PARAMETER_NAME          # Global
/application-name/environment/staging/    # Environment-specific
/application-name/service/api/           # Service-specific
```

### 4. **Version Control**

Parameter Store automatically versions parameters:

```bash
# Get specific version
aws ssm get-parameter --name "/better-call-buffet/DATABASE_URL" --version-number 2

# Get parameter history
aws ssm get-parameter-history --name "/better-call-buffet/DATABASE_URL"
```

---

## 💡 How It Works

### Data Flow:

1. **Application Startup**: FastAPI app initializes
2. **Environment Check**: Detects `ENVIRONMENT=production`
3. **Parameter Retrieval**: Calls `get_aws_parameter_store_secrets("/better-call-buffet")`
4. **Batch Fetch**: Retrieves all parameters under `/better-call-buffet/` path
5. **Decryption**: AWS automatically decrypts SecureString parameters using KMS
6. **Configuration**: Updates application settings with retrieved values

### Security Model:

```mermaid
graph LR
    A[GitHub Actions] --> B[AWS IAM Role]
    B --> C[Parameter Store]
    C --> D[KMS Encryption]
    E[FastAPI App] --> F[Parameter Store]
    F --> G[KMS Decryption]
    G --> H[Application Config]
```

---

## 🔍 Troubleshooting

### Common Issues:

1. **Access Denied Error**

   ```
   ClientError: An error occurred (AccessDenied) when calling the GetParameter operation
   ```

   **Solution**: Check IAM permissions for Parameter Store and KMS

2. **Parameter Not Found**

   ```
   ClientError: An error occurred (ParameterNotFound) when calling the GetParameter operation
   ```

   **Solution**: Verify parameter name and path are correct

3. **KMS Decryption Error**
   ```
   ClientError: An error occurred (AccessDenied) when calling the Decrypt operation
   ```
   **Solution**: Add KMS decrypt permissions for the default SSM key

### Testing Commands:

```bash
# Test IAM permissions
aws sts get-caller-identity

# Test parameter access
aws ssm describe-parameters --filters "Key=Name,Values=/better-call-buffet"

# Test KMS access
aws kms describe-key --key-id alias/aws/ssm
```

---

## 📊 Cost Impact

### Monthly Savings:

- **Secrets Manager**: 3 secrets × $0.40 = **$1.20/month**
- **Parameter Store**: 3 parameters × $0.00 = **$0.00/month**
- **Total Savings**: **$1.20/month** (20% of current infrastructure costs!)

### Related Concepts:

- **AWS Free Tier Optimization**: Maximizing free tier usage
- **Infrastructure as Code**: Managing secrets in version control
- **Security Best Practices**: Encryption at rest and in transit
- **Cost Engineering**: Architecting for cost efficiency

### Production Considerations:

- **High Availability**: Parameter Store is a managed service with built-in redundancy
- **Backup Strategy**: Parameter history provides automatic versioning
- **Disaster Recovery**: Parameters can be exported and imported across regions
- **Compliance**: Maintains encryption and audit logging like Secrets Manager
