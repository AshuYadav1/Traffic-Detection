# Render Deployment Guide for Traffic Violation Detection API

This guide will help you deploy your Traffic Violation Detection API to Render.

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **Model Files**: Ensure your AI model files are properly handled

## Deployment Steps

### 1. Prepare Your Repository

Make sure your repository contains these deployment files (already created):
- `requirements.txt` - Python dependencies
- `render.yaml` - Render service configuration
- `Procfile` - Process definition
- `start.sh` - Startup script
- `env.example` - Environment variables template

### 2. Connect to Render

1. Log into your Render dashboard
2. Click "New +" and select "Blueprint"
3. Connect your GitHub repository
4. Select the repository containing your backend code
5. Choose the branch (usually `main` or `master`)

### 3. Configure Environment Variables

In your Render service settings, add these environment variables:

#### Required Variables:
```
DATABASE_URL=postgresql://username:password@hostname:port/database_name
REDIS_URL=redis://username:password@hostname:port
UPLOAD_DIR=/tmp/uploads
EVIDENCE_DIR=/tmp/evidence
ALLOWED_ORIGINS=*
```

#### Optional Variables (with defaults):
```
MODEL_SIZE=small
DEFAULT_CONFIDENCE_THRESHOLD=0.5
DEFAULT_IOU_THRESHOLD=0.45
MIN_MOTORCYCLE_AREA=3000
HELMET_CHECK_CONFIDENCE=0.6
DEFAULT_TRAFFIC_DIRECTION=right
```

#### Email Configuration (Optional):
```
GMAIL_USERNAME=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password
GMAIL_FROM=your_email@gmail.com
```

### 4. Database Setup

1. Create a PostgreSQL database service in Render:
   - Go to "New +" → "PostgreSQL"
   - Choose a name (e.g., `traffic-violation-db`)
   - Select the free plan for testing
   - Note the connection details

2. Update your `DATABASE_URL` environment variable with the PostgreSQL connection string from Render.

### 5. Redis Setup (Optional)

1. Create a Redis service in Render:
   - Go to "New +" → "Redis"
   - Choose a name (e.g., `traffic-violation-redis`)
   - Select the free plan
   - Note the connection details

2. Update your `REDIS_URL` environment variable.

### 6. Deploy

1. Click "Create Web Service"
2. Render will automatically:
   - Install dependencies from `requirements.txt`
   - Run the startup script
   - Start your FastAPI application
   - Provide you with a public URL

### 7. Post-Deployment Setup

#### Model Files
The deployment script will automatically download the YOLO model. For custom models (SVM, PCA):
1. Upload them to your repository in the `models/` directory, or
2. Use a cloud storage service and download them in the startup script

#### Database Initialization
The startup script will create database tables automatically.

## Important Notes

### File Storage Limitations
- Render's ephemeral filesystem means uploaded files are lost on restart
- For production, integrate with cloud storage (AWS S3, Google Cloud Storage)
- The current setup uses `/tmp/` directories which are cleared on restart

### Performance Considerations
- Free tier has limited CPU and memory
- Video processing is resource-intensive
- Consider upgrading to a paid plan for production use
- Implement file size limits and processing queues for better performance

### Security
- Update `ALLOWED_ORIGINS` to specific domains for production
- Use environment variables for all sensitive configuration
- Enable HTTPS (automatic on Render)

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check the build logs in Render dashboard
   - Ensure all dependencies are in `requirements.txt`
   - Verify Python version compatibility

2. **Memory Issues**
   - Reduce model size if using free tier
   - Implement processing queues
   - Consider upgrading to a paid plan

3. **File Upload Issues**
   - Check file size limits
   - Ensure upload directories are properly created
   - Verify CORS settings

4. **Database Connection Issues**
   - Verify `DATABASE_URL` is correctly set
   - Check PostgreSQL service status
   - Ensure firewall rules allow connections

### Monitoring

1. Use Render's built-in logs to monitor your application
2. Set up health check endpoints (already configured at `/health`)
3. Monitor resource usage in the Render dashboard

## API Endpoints

Once deployed, your API will be available at:
- **Base URL**: `https://your-service-name.onrender.com`
- **API Documentation**: `https://your-service-name.onrender.com/docs`
- **Health Check**: `https://your-service-name.onrender.com/health`

## Frontend Integration

Update your Flutter admin dashboard to use the deployed API URL:
```dart
const String baseUrl = 'https://your-service-name.onrender.com';
```

## Support

- Check Render documentation: [render.com/docs](https://render.com/docs)
- Monitor application logs in Render dashboard
- Use the health check endpoint to verify service status

## Scaling

For production deployment:
1. Upgrade to a paid plan for better performance
2. Implement proper cloud storage for file uploads
3. Use a managed Redis service for better reliability
4. Set up proper monitoring and alerting
5. Implement rate limiting and authentication
