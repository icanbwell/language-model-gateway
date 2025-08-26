# Image Generation Setup Guide

This guide helps you set up and troubleshoot image generation in the language-model-gateway.

## Required Environment Variables

### For OpenAI DALL-E Image Generation

```bash
# Required: Your OpenAI API key 
OPENAI_API_KEY=sk-your-actual-openai-api-key-here

# Required: Local directory to save generated images
IMAGE_GENERATION_PATH=/path/to/your/image/directory

# Required: Base URL where images will be served
IMAGE_GENERATION_URL=http://localhost:5050/image_generation
```

### For AWS Bedrock Image Generation (Optional)

```bash
# Optional: AWS credentials profile for Bedrock
AWS_CREDENTIALS_PROFILE=your-aws-profile-name
```

## Setup Steps

1. **Set OpenAI API Key**
   ```bash
   export OPENAI_API_KEY=sk-your-actual-openai-api-key-here
   ```
   Get your API key from: https://platform.openai.com/api-keys

2. **Configure Image Storage**
   ```bash
   # For local storage
   export IMAGE_GENERATION_PATH=/tmp/images
   mkdir -p /tmp/images
   
   # For S3 storage (optional)
   export IMAGE_GENERATION_PATH=s3://your-bucket/path/
   ```

3. **Set Image Serving URL**
   ```bash
   export IMAGE_GENERATION_URL=http://localhost:5050/image_generation
   ```

## Testing Image Generation

### Test with curl

```bash
curl -X POST http://localhost:5050/api/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a white siamese cat",
    "model": "dall-e-3",
    "size": "1024x1024",
    "response_format": "url"
  }'
```

### Test with OpenAI Python client

```python
from openai import OpenAI

client = OpenAI(
    api_key="fake-api-key",  # Not needed for local gateway
    base_url="http://localhost:5050/api/v1"
)

response = client.images.generate(
    prompt="a white siamese cat",
    model="dall-e-3",
    size="1024x1024"
)

print(response.data[0].url)
```

## Common Issues and Solutions

### 1. "IMAGE_GENERATION_PATH environment variable must be set"

**Solution:** Set the path where images should be saved:
```bash
export IMAGE_GENERATION_PATH=/tmp/images
mkdir -p /tmp/images
```

### 2. "IMAGE_GENERATION_URL environment variable must be set"

**Solution:** Set the base URL for serving images:
```bash
export IMAGE_GENERATION_URL=http://localhost:5050/image_generation
```

### 3. "OPENAI_API_KEY environment variable is not set"

**Solution:** Set your OpenAI API key:
```bash
export OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

### 4. "Invalid OPENAI_API_KEY detected"

**Solution:** Make sure you're using a real OpenAI API key, not a placeholder:
- Get a real API key from https://platform.openai.com/api-keys
- Replace any fake/test keys with the real one

### 5. "Failed to save image file and generate URL"

**Solutions:**
- Check that the IMAGE_GENERATION_PATH directory exists and is writable
- For S3: Ensure AWS credentials are properly configured
- Check disk space if using local storage

### 6. Connection errors or API failures

**Solutions:**
- Verify your OpenAI API key is valid and has sufficient credits
- Check internet connection
- For AWS: Verify AWS credentials and Bedrock access

## Environment File Example

Create a `.env` file:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-actual-openai-api-key-here

# Image Generation Configuration  
IMAGE_GENERATION_PATH=/tmp/images
IMAGE_GENERATION_URL=http://localhost:5050/image_generation

# Optional: AWS Configuration
AWS_CREDENTIALS_PROFILE=default
```

## Docker Compose Example

```yaml
services:
  language-model-gateway:
    # ... other configuration
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      IMAGE_GENERATION_PATH: "/usr/src/language_model_gateway/image_generation" 
      IMAGE_GENERATION_URL: "http://localhost:5050/image_generation"
    volumes:
      - ./image_generation:/usr/src/language_model_gateway/image_generation
```

---

For more help, check the logs for detailed error messages and ensure all environment variables are properly set before starting the service.