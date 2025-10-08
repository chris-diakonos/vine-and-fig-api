# Azure Blob Storage Integration

This guide explains how to configure the Vine & Fig API to use Azure Blob Storage instead of local file storage.

## Overview

The API supports two storage backends:
- **Local Storage**: Files stored on the container/server filesystem
- **Azure Blob Storage**: Files stored in Azure Blob Storage

Azure Storage is recommended for production deployments as it provides:
- **Scalability**: Handle large numbers of files without filesystem limitations
- **Reliability**: Built-in redundancy and backups
- **CDN Integration**: Easily serve files through Azure CDN for better performance
- **Lifecycle Management**: Automatic cleanup of old files
- **Cost Efficiency**: Pay only for what you store and use

## Prerequisites

1. **Azure Account**: You need an Azure subscription
2. **Storage Account**: Create an Azure Storage Account
3. **Container**: A blob container will be created automatically (default: `vine-and-fig`)
4. **SAS Token**: Generate a Shared Access Signature token for authentication

## Step-by-Step Setup

### 1. Create Azure Storage Account

```bash
# Using Azure CLI
az storage account create \
  --name vineandfigstorageVNAME \
  --resource-group your-resource-group \
  --location eastus \
  --sku Standard_LRS

# Or use Azure Portal:
# https://portal.azure.com → Storage accounts → Create
```

### 2. Generate SAS Token

#### Via Azure Portal:

1. Go to your Storage Account in Azure Portal
2. Navigate to **Security + networking** → **Shared access signature**
3. Configure the SAS settings:
   - **Allowed services**: ☑ Blob
   - **Allowed resource types**: ☑ Service, ☑ Container, ☑ Object
   - **Allowed permissions**: ☑ Read, ☑ Write, ☑ Delete, ☑ List, ☑ Add, ☑ Create
   - **Start and expiry date/time**: Set appropriate dates
   - **Allowed protocols**: HTTPS only
4. Click **Generate SAS and connection string**
5. Copy the **SAS token** (the part after the `?`)

#### Via Azure CLI:

```bash
# Generate SAS token valid for 1 year
az storage account generate-sas \
  --account-name vineandfigstorageVNAME \
  --services b \
  --resource-types sco \
  --permissions rwdlac \
  --expiry 2025-12-31T23:59:59Z \
  --https-only
```

### 3. Configure Environment Variables

#### For Docker Compose:

Edit `docker-compose.yml`:

```yaml
environment:
  - STORAGE_TYPE=azure
  - AZURE_STORAGE_ACCOUNT_NAME=vineandfigstorageVNAME
  - AZURE_STORAGE_SAS_TOKEN=sv=2021-06-08&ss=b&srt=sco&sp=rwdlac&se=2025-12-31T23:59:59Z&st=2024-01-01T00:00:00Z&spr=https&sig=yoursignaturehere
  - AZURE_STORAGE_CONTAINER_NAME=vine-and-fig
```

#### For Local Development:

Create a `.env` file:

```env
STORAGE_TYPE=azure
AZURE_STORAGE_ACCOUNT_NAME=vineandfigstorageVNAME
AZURE_STORAGE_SAS_TOKEN=sv=2021-06-08&ss=b&srt=sco&sp=rwdlac&se=2025-12-31...
AZURE_STORAGE_CONTAINER_NAME=vine-and-fig
```

Or copy the example:

```bash
cp .env.azure.example .env
# Edit .env with your actual credentials
```

### 4. Start the Application

```bash
# Using Docker Compose
docker-compose down
docker-compose build  # Rebuild to include Azure dependencies
docker-compose up -d

# Check logs to verify Azure connection
docker-compose logs -f
```

You should see log messages indicating Azure Storage is being used:

```
INFO: Azure container 'vine-and-fig' is ready
INFO: Uploaded file to Azure: models/abc123.gltf
```

## Container Structure

Files are organized in the container with prefixes:

```
vine-and-fig/
├── models/
│   ├── uuid1.gltf
│   ├── uuid2.gltf
│   └── ...
└── drawings/
    ├── uuid1_plan.svg
    ├── uuid1_elevation.svg
    └── ...
```

## File URLs

When using Azure Storage, generated file URLs will point directly to Azure:

```
https://vineandfigstorageVNAME.blob.core.windows.net/vine-and-fig/models/uuid.gltf
https://vineandfigstorageVNAME.blob.core.windows.net/vine-and-fig/drawings/uuid_plan.svg
```

These URLs are publicly accessible if your container has public read access, or you can serve them through your API with authentication.

## Security Best Practices

### 1. Use Separate SAS Tokens

For production, create different SAS tokens:
- **Backend API**: Read, Write, Delete, List permissions
- **Frontend Access**: Read-only permissions for public access

### 2. Set Expiry Dates

Always set an expiry date on SAS tokens and rotate them regularly:

```bash
# Generate new token before expiry
az storage account generate-sas \
  --account-name vineandfigstorageVNAME \
  --services b \
  --resource-types sco \
  --permissions rwdlac \
  --expiry 2026-12-31T23:59:59Z \
  --https-only
```

### 3. Use Azure Key Vault (Production)

Store credentials in Azure Key Vault instead of environment variables:

```yaml
environment:
  - STORAGE_TYPE=azure
  - AZURE_KEY_VAULT_NAME=your-keyvault
  - AZURE_KEY_VAULT_SECRET_NAME=storage-sas-token
```

### 4. Enable Container Public Access (Optional)

If you want files to be publicly accessible:

```bash
# Make container publicly readable
az storage container set-permission \
  --name vine-and-fig \
  --account-name vineandfigstorageVNAME \
  --public-access blob
```

## Lifecycle Management

Set up automatic deletion of old files using Azure Lifecycle Management:

### Via Azure Portal:

1. Go to your Storage Account
2. Navigate to **Data management** → **Lifecycle management**
3. Add a rule:
   - **Rule name**: DeleteOldModels
   - **Rule scope**: Limit blobs with filters
   - **Blob type**: Block blobs
   - **Blob subtype**: Base blobs
   - **Filter by**: Prefix starts with `models/` or `drawings/`
4. Set action:
   - **Delete the blob**: 7 days after last modification

### Via Azure CLI:

```bash
# Create lifecycle policy JSON
cat > lifecycle-policy.json << 'EOF'
{
  "rules": [
    {
      "enabled": true,
      "name": "DeleteOldFiles",
      "type": "Lifecycle",
      "definition": {
        "actions": {
          "baseBlob": {
            "delete": {
              "daysAfterModificationGreaterThan": 7
            }
          }
        },
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["models/", "drawings/"]
        }
      }
    }
  ]
}
EOF

# Apply the policy
az storage account management-policy create \
  --account-name vineandfigstorageVNAME \
  --policy @lifecycle-policy.json
```

## Monitoring

### Check Storage Usage:

```bash
# Via Azure CLI
az storage account show-usage \
  --account-name vineandfigstorageVNAME

# List all blobs
az storage blob list \
  --container-name vine-and-fig \
  --account-name vineandfigstorageVNAME \
  --sas-token "your-sas-token"
```

### Via Azure Portal:

1. Go to your Storage Account
2. Navigate to **Monitoring** → **Metrics**
3. View:
   - Storage capacity
   - Number of requests
   - Data egress (bandwidth)

## Troubleshooting

### Error: "Environment variable AZURE_STORAGE_ACCOUNT_NAME is not set"

Make sure you've set the environment variables correctly in your docker-compose.yml or .env file.

### Error: "Failed to create BlobServiceClient"

Check your SAS token:
- Ensure it hasn't expired
- Verify all required permissions are granted
- Make sure the token includes the leading `?` character

### Files Not Appearing in Azure

Check the application logs:

```bash
docker-compose logs -f api
```

Look for errors during upload. Common issues:
- Insufficient permissions in SAS token
- Container doesn't exist (should be created automatically)
- Network connectivity issues

### Slow Upload Speeds

- Choose an Azure region close to your deployment
- Use Azure CDN for serving files
- Consider upgrading your storage account SKU

## Cost Estimation

Azure Blob Storage pricing (example for US East):
- **Storage**: ~$0.018 per GB/month (Hot tier)
- **Transactions**: 
  - Write operations: $0.05 per 10,000 transactions
  - Read operations: $0.004 per 10,000 transactions
- **Data transfer**: First 100 GB/month free

For 1000 models/month at ~5MB each:
- Storage: 5 GB = ~$0.09/month
- Writes: 1000 = ~$0.005
- Reads (1000/month): ~$0.0004
- **Total: ~$0.10/month**

## Switching Between Local and Azure

To switch between storage backends, just change the `STORAGE_TYPE` environment variable:

```yaml
# Use local storage
environment:
  - STORAGE_TYPE=local

# Use Azure storage
environment:
  - STORAGE_TYPE=azure
  - AZURE_STORAGE_ACCOUNT_NAME=...
  - AZURE_STORAGE_SAS_TOKEN=...
```

No code changes needed! The application automatically uses the configured storage backend.

## Additional Resources

- [Azure Blob Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [Azure Storage Pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/)
- [SAS Token Best Practices](https://docs.microsoft.com/en-us/azure/storage/common/storage-sas-overview)
- [Azure Storage Security](https://docs.microsoft.com/en-us/azure/storage/common/storage-security-guide)
