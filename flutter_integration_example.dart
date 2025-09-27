// Flutter Integration Example for Traffic Violation Detection API
// This file shows how to integrate the backend API with your Flutter applications

import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

class TrafficViolationAPI {
  static const String baseUrl = 'http://localhost:8000/api/v1';
  
  // Upload video for processing
  static Future<Map<String, dynamic>> uploadVideo({
    required File videoFile,
    String trafficDirection = 'right',
    double confidenceThreshold = 0.5,
    int minMotorcycleArea = 3000,
  }) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/videos/upload'),
      );
      
      request.files.add(
        await http.MultipartFile.fromPath('file', videoFile.path),
      );
      
      request.fields.addAll({
        'traffic_direction': trafficDirection,
        'confidence_threshold': confidenceThreshold.toString(),
        'min_motorcycle_area': minMotorcycleArea.toString(),
      });
      
      var response = await request.send();
      var responseBody = await response.stream.bytesToString();
      
      if (response.statusCode == 200) {
        return jsonDecode(responseBody);
      } else {
        throw Exception('Upload failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error uploading video: $e');
    }
  }
  
  // Get job status
  static Future<Map<String, dynamic>> getJobStatus(String jobId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/jobs/$jobId'),
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to get job status: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error getting job status: $e');
    }
  }
  
  // Get violations for a job
  static Future<List<Map<String, dynamic>>> getJobViolations(String jobId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/jobs/$jobId/violations'),
      );
      
      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(jsonDecode(response.body));
      } else {
        throw Exception('Failed to get violations: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error getting violations: $e');
    }
  }
  
  // Get violation statistics
  static Future<Map<String, dynamic>> getViolationStats({int days = 30}) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/violations/stats?days=$days'),
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to get stats: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error getting stats: $e');
    }
  }
  
  // Download processed video
  static Future<void> downloadProcessedVideo(String jobId, String savePath) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/videos/download/$jobId'),
      );
      
      if (response.statusCode == 200) {
        final file = File(savePath);
        await file.writeAsBytes(response.bodyBytes);
      } else {
        throw Exception('Failed to download video: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error downloading video: $e');
    }
  }
  
  // Get evidence image URL
  static String getEvidenceImageUrl(String jobId, String filename) {
    return '$baseUrl/videos/evidence/$jobId/$filename';
  }
}

// WebSocket for real-time updates
class ViolationWebSocket {
  late WebSocketChannel channel;
  String? currentJobId;
  
  void connect() {
    channel = WebSocketChannel.connect(
      Uri.parse('ws://localhost:8000/api/v1/ws/live'),
    );
  }
  
  void subscribeToJob(String jobId) {
    currentJobId = jobId;
    channel.sink.add(jsonEncode({
      'type': 'subscribe_job',
      'job_id': jobId,
    }));
  }
  
  Stream<Map<String, dynamic>> get messageStream {
    return channel.stream.map((data) {
      return jsonDecode(data) as Map<String, dynamic>;
    });
  }
  
  void disconnect() {
    channel.sink.close();
  }
}

// Example usage in a Flutter widget
class VideoUploadWidget extends StatefulWidget {
  @override
  _VideoUploadWidgetState createState() => _VideoUploadWidgetState();
}

class _VideoUploadWidgetState extends State<VideoUploadWidget> {
  File? selectedVideo;
  String? jobId;
  String status = 'idle';
  ViolationWebSocket? webSocket;
  Map<String, dynamic>? jobStatus;
  List<Map<String, dynamic>> violations = [];
  
  @override
  void initState() {
    super.initState();
    _setupWebSocket();
  }
  
  void _setupWebSocket() {
    webSocket = ViolationWebSocket();
    webSocket!.connect();
    
    webSocket!.messageStream.listen((data) {
      setState(() {
        if (data['type'] == 'job_progress') {
          // Handle progress updates
          print('Progress: ${data['progress']}');
        } else if (data['type'] == 'job_completed') {
          // Handle completion
          print('Job completed: ${data['result']}');
          _loadJobStatus();
        } else if (data['type'] == 'violation_detected') {
          // Handle new violation
          print('Violation detected: ${data['violation']}');
          _loadViolations();
        }
      });
    });
  }
  
  Future<void> _uploadVideo() async {
    if (selectedVideo == null) return;
    
    setState(() {
      status = 'uploading';
    });
    
    try {
      final result = await TrafficViolationAPI.uploadVideo(
        videoFile: selectedVideo!,
        trafficDirection: 'right',
        confidenceThreshold: 0.5,
      );
      
      setState(() {
        jobId = result['job_id'];
        status = 'processing';
      });
      
      // Subscribe to job updates
      webSocket?.subscribeToJob(jobId!);
      
    } catch (e) {
      setState(() {
        status = 'error';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Upload failed: $e')),
      );
    }
  }
  
  Future<void> _loadJobStatus() async {
    if (jobId == null) return;
    
    try {
      final status = await TrafficViolationAPI.getJobStatus(jobId!);
      setState(() {
        jobStatus = status;
        if (status['status'] == 'completed') {
          this.status = 'completed';
        }
      });
    } catch (e) {
      print('Error loading job status: $e');
    }
  }
  
  Future<void> _loadViolations() async {
    if (jobId == null) return;
    
    try {
      final violations = await TrafficViolationAPI.getJobViolations(jobId!);
      setState(() {
        this.violations = violations;
      });
    } catch (e) {
      print('Error loading violations: $e');
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Traffic Violation Detection')),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          children: [
            // Video selection
            ElevatedButton(
              onPressed: () async {
                // Implement video picker
                // selectedVideo = await pickVideo();
                setState(() {});
              },
              child: Text(selectedVideo == null ? 'Select Video' : 'Video Selected'),
            ),
            
            SizedBox(height: 16),
            
            // Upload button
            if (selectedVideo != null)
              ElevatedButton(
                onPressed: status == 'idle' ? _uploadVideo : null,
                child: Text('Upload and Process'),
              ),
            
            SizedBox(height: 16),
            
            // Status display
            Text('Status: $status'),
            
            if (jobId != null) ...[
              SizedBox(height: 16),
              Text('Job ID: $jobId'),
              
              // Job status
              if (jobStatus != null)
                Card(
                  child: Padding(
                    padding: EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Total Violations: ${jobStatus!['total_violations']}'),
                        Text('Red Light: ${jobStatus!['red_light_violations']}'),
                        Text('Helmet: ${jobStatus!['helmet_violations']}'),
                        Text('Wrong Way: ${jobStatus!['wrong_way_violations']}'),
                      ],
                    ),
                  ),
                ),
              
              // Violations list
              if (violations.isNotEmpty) ...[
                SizedBox(height: 16),
                Text('Detected Violations:', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                Expanded(
                  child: ListView.builder(
                    itemCount: violations.length,
                    itemBuilder: (context, index) {
                      final violation = violations[index];
                      return Card(
                        child: ListTile(
                          title: Text('${violation['violation_type']} - ${violation['vehicle_type']}'),
                          subtitle: Text('Confidence: ${violation['confidence']}'),
                          trailing: Image.network(
                            TrafficViolationAPI.getEvidenceImageUrl(jobId!, 'evidence_image.jpg'),
                            width: 50,
                            height: 50,
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
  
  @override
  void dispose() {
    webSocket?.disconnect();
    super.dispose();
  }
}
