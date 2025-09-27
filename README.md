# Traffic Violation Detection API

A comprehensive AI-powered traffic violation detection system built with FastAPI, YOLOv8, and machine learning models for helmet detection.

## Features

- **Red Light Violation Detection**: Detects vehicles crossing stop lines when traffic lights are red
- **Helmet Violation Detection**: Uses SVM + PCA machine learning to detect motorcyclists without helmets
- **Wrong Way Detection**: Tracks vehicle movement patterns to identify vehicles going against traffic flow
- **Real-time Processing**: WebSocket support for live video stream processing
- **Evidence Capture**: Automatically saves violation images with annotations
- **REST API**: Complete REST API for video upload, processing, and result retrieval
- **Database Integration**: SQLAlchemy-based database for storing violations and metadata

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- Trained ML models (SVM and PCA pickle files)

### Installation

1. **Clone and setup**:
```bash
cd BACKEND
pip install -r requirements.txt
```

2. **Prepare model files**:
```bash
mkdir -p models
# Copy your trained models to the models directory:
# - svm_model.pkl
# - pca.pkl
```

3. **Run the application**:
```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

### Docker Deployment

1. **Using Docker Compose** (recommended):
```bash
docker-compose up -d
```

2. **Manual Docker build**:
```bash
docker build -t traffic-violation-api .
docker run -p 8000:8000 traffic-violation-api
```

## API Endpoints

### Video Processing
- `POST /api/v1/videos/upload` - Upload video for processing
- `GET /api/v1/videos/download/{job_id}` - Download processed video
- `GET /api/v1/videos/evidence/{job_id}/{filename}` - Get evidence images

### Violations
- `GET /api/v1/violations/` - List violations with filtering
- `GET /api/v1/violations/stats` - Get violation statistics
- `GET /api/v1/violations/{violation_id}` - Get specific violation
- `PUT /api/v1/violations/{violation_id}/verify` - Verify violation
- `DELETE /api/v1/violations/{violation_id}` - Delete violation

### Jobs
- `GET /api/v1/jobs/` - List processing jobs
- `GET /api/v1/jobs/{job_id}` - Get job details
- `DELETE /api/v1/jobs/{job_id}` - Delete job
- `GET /api/v1/jobs/{job_id}/violations` - Get job violations

### WebSocket
- `WS /api/v1/ws/live` - Live processing updates
- `WS /api/v1/ws/monitoring` - Real-time monitoring

## Usage Examples

### Upload Video for Processing

```python
import requests

# Upload video
with open("traffic_video.mp4", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/videos/upload",
        files={"file": f},
        data={
            "traffic_direction": "right",
            "confidence_threshold": 0.5,
            "min_motorcycle_area": 3000
        }
    )

job_data = response.json()
print(f"Job ID: {job_data['job_id']}")
```

### Get Processing Results

```python
# Check job status
job_response = requests.get(f"http://localhost:8000/api/v1/jobs/{job_data['job_id']}")
job = job_response.json()

if job['status'] == 'completed':
    # Download processed video
    video_response = requests.get(f"http://localhost:8000/api/v1/videos/download/{job_data['job_id']}")
    with open("processed_video.mp4", "wb") as f:
        f.write(video_response.content)
```

### WebSocket for Real-time Updates

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/live');

ws.onopen = () => {
    // Subscribe to job updates
    ws.send(JSON.stringify({
        type: 'subscribe_job',
        job_id: 'your-job-id'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'job_progress') {
        console.log(`Progress: ${data.progress.frame_count}/${data.progress.total_frames}`);
    } else if (data.type === 'violation_detected') {
        console.log(`Violation detected: ${data.violation.violation_type}`);
    }
};
```

## Configuration

Create a `.env` file based on `env.example`:

```bash
cp env.example .env
# Edit .env with your settings
```

Key configuration options:
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection for caching
- `ALLOWED_ORIGINS`: CORS origins for your Flutter apps
- `MAX_FILE_SIZE`: Maximum video file size
- `DEFAULT_TRAFFIC_DIRECTION`: Expected traffic flow direction

## Database Schema

The system uses the following main tables:

- **violations**: Stores detected violations with evidence
- **processing_jobs**: Tracks video processing jobs
- **evidence**: Links to violation images and videos

## Integration with Flutter Apps

### Admin Dashboard Integration

```dart
// Upload video
final response = await http.post(
  Uri.parse('http://your-api-url/api/v1/videos/upload'),
  headers: {'Content-Type': 'multipart/form-data'},
  body: {
    'file': videoFile,
    'traffic_direction': 'right',
    'confidence_threshold': '0.5',
  },
);

// Get violations
final violationsResponse = await http.get(
  Uri.parse('http://your-api-url/api/v1/violations/'),
);
```

### Mobile Client Integration

```dart
// Real-time processing with WebSocket
class ViolationWebSocket {
  late WebSocketChannel channel;
  
  void connect() {
    channel = WebSocketChannel.connect(
      Uri.parse('ws://your-api-url/api/v1/ws/live'),
    );
    
    channel.stream.listen((data) {
      final message = jsonDecode(data);
      // Handle real-time updates
    });
  }
}
```

## Deployment

### Production Deployment

1. **Environment Setup**:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/traffic_violations"
export REDIS_URL="redis://localhost:6379"
```

2. **Database Migration**:
```bash
# The database tables are created automatically on startup
# For production, consider using Alembic for migrations
```

3. **Reverse Proxy** (Nginx):
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Cloud Deployment

The API is containerized and can be deployed on:
- **AWS**: ECS, EKS, or EC2 with RDS and ElastiCache
- **Google Cloud**: Cloud Run, GKE, or Compute Engine
- **Azure**: Container Instances, AKS, or App Service
- **DigitalOcean**: App Platform or Droplets

## Monitoring and Analytics

The system provides:
- Real-time violation statistics
- Processing job monitoring
- WebSocket-based live updates
- Evidence image storage and retrieval
- Violation verification workflow

## Troubleshooting

### Common Issues

1. **Model files not found**:
   - Ensure `svm_model.pkl` and `pca.pkl` are in the `models/` directory
   - Check file permissions

2. **Memory issues with large videos**:
   - Increase Docker memory limits
   - Consider video preprocessing for size reduction

3. **Database connection errors**:
   - Verify `DATABASE_URL` configuration
   - Ensure database service is running

### Performance Optimization

- Use GPU acceleration for YOLO model (requires CUDA)
- Implement video chunking for large files
- Add Redis caching for frequent queries
- Consider horizontal scaling with load balancers

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
