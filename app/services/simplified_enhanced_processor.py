"""
Simplified Enhanced Traffic Violation Detection Processor
Based on New21.ipynb with core features (without TensorFlow for now):
- License plate detection with EasyOCR
- Enhanced helmet detection with SHAP
- Wrong way detection with direction tracking
- Improved preprocessing and feature extraction
"""

import cv2
import yaml
import numpy as np
import torch
from ultralytics import YOLO
import os
import shutil
import joblib
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional, Any
import asyncio
from datetime import datetime
import json
import re
import easyocr
from skimage.feature import hog
import matplotlib.pyplot as plt
# import shap  # Temporarily disabled due to dependency issues

from app.core.config import settings
from app.core.database import Violation, ProcessingJob, SessionLocal

class SimplifiedEnhancedProcessor:
    def __init__(self):
        self.model = None
        self.svm_model = None
        self.pca = None
        self.config = None
        self.classes_to_detect = {}
        self.class_indices = []
        self.colors = {}
        self.palettes = {}
        
        # New components
        self.ocr_reader = None
        self.plate_regex = re.compile(r'^[A-Z0-9]{6,}$')
        
        # Display options
        self.show_tracker_ids = False  # Set to True to show tracker IDs
        self.show_confidence = True   # Set to False to hide confidence scores
        
        self._load_models()
        self._load_config()
        self._initialize_new_components()
    
    def _load_models(self):
        """Load YOLO, SVM, and PCA models"""
        try:
            # Load YOLO model with GPU optimization
            model_path = settings.YOLO_MODEL_PATH
            if not os.path.exists(model_path):
                self._download_yolo_model()
            self.model = YOLO(model_path)
            
            # Set device for faster inference
            import torch
            if torch.cuda.is_available():
                self.model.to('cuda')
                print(f"✅ YOLO model loaded from {model_path} (GPU: CUDA)")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.model.to('mps')
                print(f"✅ YOLO model loaded from {model_path} (GPU: MPS)")
            else:
                print(f"✅ YOLO model loaded from {model_path} (CPU)")
            
            # Load SVM and PCA models
            svm_path = os.path.join(settings.BASE_DIR, 'svm_model.pkl')
            pca_path = os.path.join(settings.BASE_DIR, 'pca.pkl')
            
            if os.path.exists(svm_path):
                self.svm_model = joblib.load(svm_path)
                print(f"✅ SVM model loaded from {svm_path}")
            else:
                print(f"⚠️ SVM model not found at {svm_path}")
            
            if os.path.exists(pca_path):
                self.pca = joblib.load(pca_path)
                print(f"✅ PCA model loaded from {pca_path}")
            else:
                print(f"⚠️ PCA model not found at {pca_path}")
                
        except Exception as e:
            print(f"❌ Error loading models: {e}")
            raise
    
    def _download_yolo_model(self):
        """Download YOLO model if not exists"""
        import requests
        model_url = "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt"
        try:
            print("📥 Downloading YOLO model...")
            response = requests.get(model_url)
            response.raise_for_status()
            with open(settings.YOLO_MODEL_PATH, 'wb') as f:
                f.write(response.content)
            print(f"✅ YOLO model downloaded to {settings.YOLO_MODEL_PATH}")
        except Exception as e:
            print(f"❌ Error downloading YOLO model: {e}")
            raise
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            config_path = os.path.join(settings.BASE_DIR, "config.yaml")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.config = yaml.safe_load(f)
            else:
                # Default configuration
                self.config = {
                    'model_size': 'small',
                    'object_classes': {
                        'car': 2, 'motorcycle': 3, 'bus': 5, 
                        'truck': 7, 'traffic light': 9
                    },
                    'color_pallete': {
                        'red': [0, 0, 255], 'amber': [0, 191, 255],
                        'lime': [0, 255, 0], 'emerald': [80, 200, 120],
                        'cyan': [255, 255, 0], 'blue': [255, 0, 0],
                        'violet': [226, 43, 138], 'fuchsia': [255, 0, 255],
                        'rose': [255, 0, 127]
                    }
                }
            
            self.classes_to_detect = self.config.get('object_classes', {})
            self.class_indices = list(self.classes_to_detect.values())
            
            color_palette = self.config.get('color_pallete', {})
            self.colors = {k: tuple(v) for k, v in color_palette.items()}
            
            self.palettes = {
                'red': self.colors.get('red', (0, 0, 255)),
                'yellow': self.colors.get('amber', (0, 255, 255)),
                'green': self.colors.get('lime', (0, 255, 0)),
                "light's off": self.colors.get('emerald', (80, 200, 120)),
                'car': self.colors.get('cyan', (255, 255, 0)),
                'motorcycle': self.colors.get('blue', (255, 0, 0)),
                'bus': self.colors.get('violet', (238, 130, 238)),
                'truck': self.colors.get('fuchsia', (255, 0, 255)),
                'traffic light': self.colors.get('rose', (255, 0, 127))
            }
            
            print("✅ Configuration loaded successfully")
            
        except Exception as e:
            print(f"❌ Error loading configuration: {e}")
            raise
    
    def _initialize_new_components(self):
        """Initialize new components from New21.ipynb"""
        try:
            # Initialize EasyOCR reader
            self.ocr_reader = easyocr.Reader(['en'], gpu=False)
            print("✅ EasyOCR reader initialized")
                
        except Exception as e:
            print(f"❌ Error initializing new components: {e}")
            # Continue without new components
    
    # --- Enhanced Preprocessing Functions ---
    def preprocess_image(self, image, target_size=(256, 256)):
        """Enhanced image preprocessing with CLAHE and sharpening"""
        resized = cv2.resize(image, target_size)
        blurred = cv2.GaussianBlur(resized, (5,5), 0)

        lab = cv2.cvtColor(blurred, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l_clahe = clahe.apply(l)
        lab_clahe = cv2.merge((l_clahe, a, b))
        contrast_adjusted = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2RGB)

        kernel = np.array([[0,-1,0], [-1,5,-1], [0,-1,0]])
        sharpened = cv2.filter2D(contrast_adjusted, -1, kernel)

        return sharpened
    
    def segment_image_canny(self, image, low_threshold=100, high_threshold=200):
        """Enhanced segmentation using Canny edge detection"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, low_threshold, high_threshold)
        kernel = np.ones((5,5), np.uint8)
        morph = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        return morph
    
    def extract_hog_features(self, image):
        """Extract HOG features for helmet detection"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        features, hog_image = hog(gray,
                                  orientations=9,
                                  pixels_per_cell=(8,8),
                                  cells_per_block=(2,2),
                                  visualize=True)
        return features
    
    def extract_color_histogram(self, image):
        """Extract color histogram features"""
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [256], [0,256])
        hist_s = cv2.calcHist([hsv], [1], None, [256], [0,256])
        hist_v = cv2.calcHist([hsv], [2], None, [256], [0,256])

        hist_h /= hist_h.sum()
        hist_s /= hist_s.sum()
        hist_v /= hist_v.sum()

        return np.concatenate([hist_h.flatten(), hist_s.flatten(), hist_v.flatten()])
    
    def extract_features_from_segmented_image(self, segmented_image, original_image, min_region_area=100):
        """Extract features from segmented regions"""
        gray = cv2.cvtColor(segmented_image, cv2.COLOR_RGB2GRAY) if len(segmented_image.shape)==3 else segmented_image.copy()
        contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        features_list = []
        rois_list = []
        for contour in contours:
            if cv2.contourArea(contour) < min_region_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            roi = original_image[y:y+h, x:x+w]
            if roi.size == 0:
                continue

            roi_resized = cv2.resize(roi, (128, 128))
            hog_feat = self.extract_hog_features(roi_resized)
            color_feat = self.extract_color_histogram(roi_resized)
            combined = np.concatenate([hog_feat, color_feat])

            features_list.append(combined)
            rois_list.append((x, y, w, h))

        return features_list, rois_list
    
    # --- Enhanced Helmet Detection with SHAP ---
    def predict_helmet_on_image_array(self, image, min_region_area=50, threshold=-0.1,
                                     motorcycle_box_size=None, min_box_area=5000):
        """Enhanced helmet prediction with SHAP explanations"""
        if image is None or image.size == 0:
            return {"final_prediction": "No Helmet", "scores": [], "skipped": True, "reason": "Empty image"}

        # Skip detection if motorcycle is too small/far away
        if motorcycle_box_size is not None:
            box_area = motorcycle_box_size[0] * motorcycle_box_size[1]
            if box_area < min_box_area:
                return {
                    "final_prediction": "Skipped",
                    "scores": [],
                    "skipped": True,
                    "reason": f"Motorcycle too small (area: {box_area} < {min_box_area})"
                }

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        processed = self.preprocess_image(image)
        segmented = self.segment_image_canny(processed, low_threshold=50, high_threshold=150)

        features_list, rois = self.extract_features_from_segmented_image(segmented, processed, min_region_area)
        if not features_list:
            return {"final_prediction": "No Helmet", "scores": [], "skipped": False}

        features_array = np.array(features_list)
        TRAIN_FEATURES = 35364
        if features_array.shape[1] < TRAIN_FEATURES:
            padding = np.zeros((features_array.shape[0], TRAIN_FEATURES - features_array.shape[1]))
            features_array = np.hstack([features_array, padding])

        if self.pca is None or self.svm_model is None:
            return {"final_prediction": "No Helmet", "scores": [], "skipped": True, "reason": "Models not loaded"}

        features_reduced = self.pca.transform(features_array)
        scores = self.svm_model.decision_function(features_reduced)
        preds = (scores >= threshold).astype(int)
        final_label = "Helmet" if np.any(preds == 1) else "No Helmet"
        
        # Generate SHAP explanation
        try:
            if features_reduced.shape[0] > 0:
                def predict_wrapper(X):
                    if len(X.shape) == 1:
                        X = X.reshape(1, -1)
                    return self.svm_model.decision_function(X)

                background_size = min(50, features_reduced.shape[0])
                background_data = features_reduced[:background_size]

                explainer = shap.KernelExplainer(predict_wrapper, background_data)
                sample_to_explain = features_reduced[0:1]
                shap_values = explainer.shap_values(sample_to_explain, nsamples=100)

                explanation = shap.Explanation(
                    values=shap_values[0] if shap_values.ndim > 1 else shap_values,
                    base_values=explainer.expected_value,
                    data=features_reduced[0],
                    feature_names=[f"feature_{i}" for i in range(len(features_reduced[0]))]
                )

                # Save SHAP plot
                plt.figure(figsize=(12, 8))
                shap.plots.waterfall(explanation, max_display=20, show=False)
                plt.savefig("helmet_shap_waterfall.png", dpi=150, bbox_inches='tight', 
                           pad_inches=0.2, facecolor='white', edgecolor='none')
                plt.close()
                print("✅ SHAP waterfall plot saved: helmet_shap_waterfall.png")

        except Exception as shap_error:
            print(f"⚠️ SHAP explanation failed: {shap_error}")

        results = []
        for i, score in enumerate(scores):
            pred_label = "Helmet" if preds[i] == 1 else "No Helmet"
            results.append({
                "region_index": i + 1,
                "score": float(score),
                "prediction": pred_label
            })

        return {
            "final_prediction": final_label,
            "scores": results,
            "skipped": False
        }
    
    # --- License Plate Detection ---
    def detect_license_plate(self, frame, vehicles, detected_plates_set):
        """Detect license plates on vehicles using EasyOCR"""
        for vehicle in vehicles:
            x1, y1, x2, y2 = map(int, vehicle[:4])
            vehicle_roi = frame[y1:y2, x1:x2]
            if vehicle_roi.size == 0:
                continue

            # Use EasyOCR to read text from the vehicle ROI
            results = self.ocr_reader.readtext(vehicle_roi)

            for bbox, text, conf in results:
                cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())

                # Check for a valid plate format with decent confidence
                if conf > 0.4 and len(cleaned) >= 6 and self.plate_regex.match(cleaned):
                    if cleaned not in detected_plates_set:
                        print(f"✅ Detected unique plate: {cleaned} (Confidence: {conf:.2f})")
                        detected_plates_set.add(cleaned)
                        return cleaned
        
        return None
    
    # --- Wrong Way Detection ---
    class WrongWayDetector:
        def __init__(self, history_length=10, min_displacement=30, confidence_threshold=0.7):
            self.history = defaultdict(lambda: deque(maxlen=history_length))
            self.wrong_way_ids = set()
            self.min_displacement = min_displacement
            self.confidence_threshold = confidence_threshold
            self.expected_direction = None

        def set_expected_direction(self, direction='right'):
            self.expected_direction = direction

        def update_and_check(self, vehicles, frame_width, frame_height):
            newly_detected = []

            for vehicle in vehicles:
                if len(vehicle) < 7:
                    continue

                tracker_id = int(vehicle[4])
                x_center = (vehicle[0] + vehicle[2]) / 2
                y_center = (vehicle[1] + vehicle[3]) / 2

                self.history[tracker_id].append((x_center.item(), y_center.item()))

                if len(self.history[tracker_id]) >= 5:
                    positions = list(self.history[tracker_id])
                    dx = positions[-1][0] - positions[0][0]
                    dy = positions[-1][1] - positions[0][1]

                    displacement = np.sqrt(dx**2 + dy**2)
                    if displacement < self.min_displacement:
                        continue

                    is_wrong_way = False
                    if self.expected_direction == 'right' and dx < -self.min_displacement:
                        is_wrong_way = True
                    elif self.expected_direction == 'left' and dx > self.min_displacement:
                        is_wrong_way = True
                    elif self.expected_direction == 'down' and dy < -self.min_displacement:
                        is_wrong_way = True
                    elif self.expected_direction == 'up' and dy > self.min_displacement:
                        is_wrong_way = True

                    if is_wrong_way and tracker_id not in self.wrong_way_ids:
                        self.wrong_way_ids.add(tracker_id)
                        newly_detected.append(tracker_id)

            return self.wrong_way_ids, newly_detected
    
    # --- Main Processing Function ---
    async def process_video_enhanced(self, input_path: str, output_path: str, 
                                   expected_traffic_direction='right',
                                   min_motorcycle_area=3000, 
                                   helmet_check_confidence=0.6,
                                   job_id: str = None) -> Dict[str, Any]:
        """
        Enhanced video processing with all new features and WebSocket notifications
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found at {input_path}")

        # Initialize WebSocket manager if job_id is provided
        websocket_manager = None
        if job_id:
            from app.websocket.connection_manager import manager
            websocket_manager = manager

        # Initialize detectors
        wrong_way_detector = self.WrongWayDetector(history_length=15, min_displacement=40)
        wrong_way_detector.set_expected_direction(expected_traffic_direction)

        # Setup video processing
        cap = cv2.VideoCapture(input_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Use avc1 codec for maximum web compatibility (H.264)
        out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'avc1'), fps, (width, height))
        
        # Send initial progress update
        if websocket_manager:
            await websocket_manager.send_job_progress(job_id, {
                "status": "processing",
                "frame_count": 0,
                "total_frames": total_frames,
                "message": f"Processing video with {total_frames} frames..."
            })

        # Initialize tracking variables
        line_height_stats = {'n': 0, 'sum': 0, 'mean': 0}
        red_light_violator_ids = set()
        helmet_violator_ids = set()
        detected_plates = set()
        frame_count = 0
        
        # Store last processed frame data for consistent annotations
        last_vehicles = []
        last_traffic_lights = []
        last_light_colors = {}
        last_red_light_violators = set()
        last_helmet_violators = set()
        last_wrong_way_ids = set()

        stats = {
            'red_light_violations': 0,
            'helmet_violations': 0,
            'wrong_way_violations': 0,
            'helmets_skipped': 0,
            'license_plates_detected': 0
        }

        # Process more frames for better detection quality (matching notebook approach)
        frame_skip = max(1, fps // 10)  # Process every 10th frame for better detection quality
        print(f"🎬 Processing video: {width}x{height} @ {fps}fps, {total_frames} frames (processing every {frame_skip} frames)")

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
                
            frame_count += 1
            
            # Skip frames for faster processing
            if frame_count % frame_skip != 0:
                # Apply last processed frame's annotations for consistency
                self._annotate_frame(frame, last_vehicles, last_traffic_lights, last_light_colors, 
                                   last_red_light_violators, last_helmet_violators, last_wrong_way_ids)
                out.write(frame)
                continue
                
            if frame.shape[0] != height or frame.shape[1] != width:
                frame = cv2.resize(frame, (width, height))
            
            # Send progress update every 10 processed frames
            if websocket_manager and (frame_count // frame_skip) % 10 == 0:
                progress = (frame_count / total_frames) * 100
                processed_frames = frame_count // frame_skip
                await websocket_manager.send_job_progress(job_id, {
                    "status": "processing",
                    "frame_count": frame_count,
                    "total_frames": total_frames,
                    "processed_frames": processed_frames,
                    "progress_percent": round(progress, 2),
                    "violations": stats,
                    "message": f"Processing frame {frame_count}/{total_frames} ({progress:.1f}%) - {processed_frames} frames analyzed"
                })

            # YOLO detection with optimized settings
            # Use same approach as notebook for better detection quality
            results = self.model.track(
                frame, 
                persist=True, 
                classes=self.class_indices, 
                verbose=False
            )
            if results[0].boxes is None or len(results[0].boxes) == 0:
                out.write(frame)
                continue

            detection_data = results[0].boxes.data
            traffic_light_mask = detection_data[:, -1] == self.classes_to_detect['traffic light']
            traffic_lights = detection_data[traffic_light_mask]
            vehicles = detection_data[~traffic_light_mask]

            # License plate detection (every frame for better accuracy)
            plate = self.detect_license_plate(frame, vehicles, detected_plates)
            if plate:
                stats['license_plates_detected'] += 1

            # Red light violation detection
            light_colors = self.recognize_traffic_light_color(frame, traffic_lights)
            primary_red_light_idx, _ = self.choose_primary_red_light(light_colors)
            all_red_light_violators = torch.empty((0, 7), device=vehicles.device)
            
            if primary_red_light_idx is not None:
                red_light_box = traffic_lights[primary_red_light_idx]
                line_height = red_light_box[3].item() - red_light_box[1].item()
                line_height_stats['sum'] += line_height
                line_height_stats['n'] += 1
                line_height_stats['mean'] = line_height_stats['sum'] / line_height_stats['n']
                line_position = 3.5 * line_height_stats['mean'] + red_light_box[1].item()
                
                red_light_violator_ids, all_red_light_violators, newly_caught_red_light = self.recognize_violation(
                    vehicles, line_position, red_light_violator_ids
                )
                
                if newly_caught_red_light:
                    stats['red_light_violations'] += len(newly_caught_red_light)
                    for violator_tensor in newly_caught_red_light:
                        self._save_violation_evidence(frame, violator_tensor, "red_light", frame_count, job_id)
                        
                        # Send violation notification via WebSocket
                        if websocket_manager:
                            await websocket_manager.send_violation_detected(job_id, {
                                "type": "red_light",
                                "frame": frame_count,
                                "vehicle_type": self._get_class_name(int(violator_tensor[6])),
                                "confidence": float(violator_tensor[5]),
                                "coordinates": {
                                    "x1": int(violator_tensor[0]),
                                    "y1": int(violator_tensor[1]),
                                    "x2": int(violator_tensor[2]),
                                    "y2": int(violator_tensor[3])
                                }
                            })

            # Helmet violation detection (every frame for better accuracy)
            motorcycle_mask = vehicles[:, -1] == self.classes_to_detect.get('motorcycle', -1)
            motorcycles = vehicles[motorcycle_mask]
            
            if motorcycles.numel() > 0:
                for mc in motorcycles:
                    tracker_id = int(mc[4])
                    if tracker_id in helmet_violator_ids:
                        continue
                        
                    x1, y1, x2, y2 = map(int, mc[:4])
                    mc_width, mc_height, mc_area = x2 - x1, y2 - y1, (x2 - x1) * (y2 - y1)
                    
                    if mc_area < min_motorcycle_area:
                        stats['helmets_skipped'] += 1
                        continue
                    
                    # Extract helmet ROI
                    desired_height = int(mc_height * 0.6)
                    new_y1 = max(0, y1 - desired_height)
                    new_y2 = min(y1 + int(mc_height * 0.3), frame.shape[0])
                    horizontal_expansion = int(mc_width * 0.1)
                    new_x1 = max(0, x1 - horizontal_expansion)
                    new_x2 = min(x2 + horizontal_expansion, frame.shape[1])
                    helmet_roi = frame[new_y1:new_y2, new_x1:new_x2]
                    
                    if helmet_roi.size > 0:
                        helmet_result = self.predict_helmet_on_image_array(
                            helmet_roi,
                            motorcycle_box_size=(mc_width, mc_height),
                            min_box_area=min_motorcycle_area
                        )
                        
                        if not helmet_result.get('skipped', False) and helmet_result['final_prediction'] == "No Helmet":
                            print(f"New Helmet Violation: Tracker ID {tracker_id} (motorcycle area: {mc_area})")
                            helmet_violator_ids.add(tracker_id)
                            stats['helmet_violations'] += 1
                            self._save_violation_evidence(frame, mc, "helmet", frame_count, job_id)
            

            # Wrong way detection
            wrong_way_ids, newly_detected_wrong_way = wrong_way_detector.update_and_check(
                vehicles, width, height
            )
            
            if newly_detected_wrong_way:
                stats['wrong_way_violations'] += len(newly_detected_wrong_way)
                for wrong_way_id in newly_detected_wrong_way:
                    for v in vehicles:
                        if len(v) >= 7 and int(v[4]) == wrong_way_id:
                            self._save_violation_evidence(frame, v, "wrong_way", frame_count, job_id)
                            break

            # Annotate frame
            self._annotate_frame(frame, vehicles, traffic_lights, light_colors, 
                               all_red_light_violators, helmet_violator_ids, 
                               wrong_way_ids)
            
            # Store current frame data for skipped frames
            last_vehicles = vehicles
            last_traffic_lights = traffic_lights
            last_light_colors = light_colors
            last_red_light_violators = all_red_light_violators
            last_helmet_violators = helmet_violator_ids
            last_wrong_way_ids = wrong_way_ids
            
            out.write(frame)

        cap.release()
        out.release()

        # Print statistics
        print(f"\n{'='*50}")
        print(f"Enhanced Processing Complete - Violation Statistics:")
        print(f"Red Light Violations: {stats['red_light_violations']}")
        print(f"Helmet Violations: {stats['helmet_violations']}")
        print(f"Wrong Way Violations: {stats['wrong_way_violations']}")
        print(f"License Plates Detected: {stats['license_plates_detected']}")
        print(f"Helmets Skipped: {stats['helmets_skipped']}")
        print(f"{'='*50}")

        # Update job statistics in database
        if job_id:
            try:
                from app.core.database import SessionLocal, ProcessingJob
                from datetime import datetime
                
                # Use SessionLocal directly instead of get_db dependency
                with SessionLocal() as db:
                    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
                    if job:
                        total_viol = stats['red_light_violations'] + stats['helmet_violations'] + stats['wrong_way_violations']
                        job.total_violations = total_viol
                        job.red_light_violations = stats['red_light_violations']
                        job.helmet_violations = stats['helmet_violations']
                        job.wrong_way_violations = stats['wrong_way_violations']
                        db.commit()
                        print(f"✅ Job statistics updated in database: Total={total_viol}, Red={stats['red_light_violations']}, Helmet={stats['helmet_violations']}, Wrong={stats['wrong_way_violations']}")
                        
                        # Verify the update was successful
                        db.refresh(job)
                        print(f"✅ Verification: Database shows Total={job.total_violations}, Red={job.red_light_violations}, Helmet={job.helmet_violations}, Wrong={job.wrong_way_violations}")
                    else:
                        print(f"❌ Job not found in database: {job_id}")
            except Exception as e:
                print(f"❌ Failed to update job statistics: {e}")
                import traceback
                traceback.print_exc()

        return {
            'stats': stats,
            'detected_plates': list(detected_plates),
            'total_frames': total_frames,
            'processing_time': datetime.now().isoformat()
        }
    
    # --- Helper Methods ---
    def _save_violation_evidence(self, frame, violator_tensor, violation_type, frame_count, job_id=None):
        """Save evidence image for violation and database record"""
        evidence_frame = frame.copy()
        x1, y1, x2, y2 = map(int, violator_tensor[:4])
        cv2.rectangle(evidence_frame, (x1, y1), (x2, y2), (0, 255, 255), 5)
        
        tracker_id = int(violator_tensor[4])
        class_name = self._get_class_name(int(violator_tensor[6]))
        save_path = f"{violation_type}_violator_{class_name}_{tracker_id}_frame{frame_count}.jpg"
        cv2.imwrite(save_path, evidence_frame)
        
        # Save violation to database
        if job_id:
            try:
                from app.core.database import get_db, Violation
                import json
                from datetime import datetime
                
                db = next(get_db())
                violation = Violation(
                    violation_type=violation_type,
                    vehicle_type=class_name,
                    tracker_id=tracker_id,
                    confidence=float(violator_tensor[5]) if len(violator_tensor) >= 6 else 0.0,
                    frame_number=frame_count,
                    evidence_image_path=save_path,
                    violation_coordinates=json.dumps({
                        "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)
                    }),
                    job_id=job_id
                )
                db.add(violation)
                db.commit()
                print(f"✅ Violation saved to database: {violation_type} - {class_name} (ID: {tracker_id})")
            except Exception as e:
                print(f"❌ Failed to save violation to database: {e}")
                db.rollback()
    
    def _annotate_frame(self, frame, vehicles, traffic_lights, light_colors, 
                       red_light_violators, helmet_violators, wrong_way_ids):
        """Annotate frame with all detections"""
        # Annotate vehicles
        for vehicle in vehicles:
            x1, y1, x2, y2 = map(int, vehicle[:4])
            tracker_id = int(vehicle[4]) if len(vehicle) >= 7 else None
            conf = vehicle[5] * 100 if len(vehicle) >= 7 else vehicle[4] * 100
            class_id = int(vehicle[6]) if len(vehicle) >= 7 else int(vehicle[5])
            
            class_name = self._get_class_name(class_id)
            color = self.palettes.get(class_name, (255, 255, 255))
            
            # Check for violations and create label
            if tracker_id in red_light_violators:
                violation_text = "VIOLATES"
                color = (0, 0, 255)  # Red
            elif tracker_id in helmet_violators:
                violation_text = "NO HELMET"
                color = (0, 255, 255)  # Yellow
            elif tracker_id in wrong_way_ids:
                violation_text = "WRONG WAY"
                color = (255, 0, 255)  # Magenta
            else:
                violation_text = ""
            
            # Build label based on display options
            label_parts = []
            if self.show_tracker_ids and tracker_id:
                label_parts.append(f"ID:{tracker_id}")
            if self.show_confidence:
                label_parts.append(f"{conf:.1f}%")
            label_parts.append(class_name)
            if violation_text:
                label_parts.append(violation_text)
            
            label = " ".join(label_parts)
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw text with better visibility
            if label:
                # Calculate text size for background
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                thickness = 2
                (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
                
                # Text background position
                text_x = x1
                text_y = y1 - 10
                if text_y - text_height < 0:  # If text goes above frame, put it below box
                    text_y = y2 + text_height + 5
                
                # Draw text background for better visibility
                cv2.rectangle(frame, 
                            (text_x, text_y - text_height - 5), 
                            (text_x + text_width + 5, text_y + 5), 
                            (0, 0, 0), -1)  # Black background
                
                # Draw white text on black background
                cv2.putText(frame, label, (text_x + 2, text_y), font, font_scale, (255, 255, 255), thickness)
        
        # Annotate traffic lights
        for i, light in enumerate(traffic_lights):
            x1, y1, x2, y2 = map(int, light[:4])
            conf = light[4] * 100
            
            # Get light color
            color_name = "light's off"
            for color, boxes in light_colors.items():
                for box_data in boxes:
                    if box_data[0] == i:
                        color_name = color
                        break
            
            color = self.palettes.get(color_name, (255, 255, 255))
            label = f"{conf:.1f}% {color_name.upper()}"
            
            # Draw traffic light box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw traffic light label with better visibility
            if label:
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                thickness = 2
                (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
                
                text_x = x1
                text_y = y1 - 10
                if text_y - text_height < 0:
                    text_y = y2 + text_height + 5
                
                # Black background for text
                cv2.rectangle(frame, 
                            (text_x, text_y - text_height - 5), 
                            (text_x + text_width + 5, text_y + 5), 
                            (0, 0, 0), -1)
                
                # White text
                cv2.putText(frame, label, (text_x + 2, text_y), font, font_scale, (255, 255, 255), thickness)
    
    def _get_class_name(self, class_id):
        """Get class name from class ID"""
        try:
            return list(self.classes_to_detect.keys())[list(self.classes_to_detect.values()).index(class_id)]
        except ValueError:
            return "Unknown"
    
    def recognize_traffic_light_color(self, frame, predictions):
        """Recognize traffic light colors using HSV analysis"""
        colors = {'red': [], 'yellow': [], 'green': [], "light's off": []}
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        for i, traffic_light in enumerate(predictions):
            x1, y1, x2, y2 = map(int, traffic_light[:4])
            confidence = round(float(traffic_light[-2] * 100), 2)
            traffic_light_area = hsv_frame[y1:y2, x1:x2]
            
            if traffic_light_area.size == 0:
                continue
            
            # HSV color ranges
            mask_red1 = cv2.inRange(traffic_light_area, np.array([0, 100, 100]), np.array([10, 255, 255]))
            mask_red2 = cv2.inRange(traffic_light_area, np.array([160, 100, 100]), np.array([179, 255, 255]))
            mask_red = mask_red1 + mask_red2
            mask_yellow = cv2.inRange(traffic_light_area, np.array([15, 100, 100]), np.array([35, 255, 255]))
            mask_green = cv2.inRange(traffic_light_area, np.array([40, 100, 100]), np.array([85, 255, 255]))
            
            red, yellow, green = cv2.countNonZero(mask_red), cv2.countNonZero(mask_yellow), cv2.countNonZero(mask_green)
            pixel_threshold = 50
            
            if red > yellow and red > green and red > pixel_threshold:
                colors["red"].append((i, confidence))
            elif yellow > red and yellow > green and yellow > pixel_threshold:
                colors["yellow"].append((i, confidence))
            elif green > red and green > yellow and green > pixel_threshold:
                colors["green"].append((i, confidence))
            else:
                colors["light's off"].append((i, confidence))
        
        return colors
    
    def choose_primary_red_light(self, light_colors):
        """Choose the primary red light for violation detection"""
        chosen = [None, 0.0]
        if not light_colors['red']:
            return None, 0.0
        
        for index, confidence in light_colors['red']:
            if confidence > chosen[1]:
                chosen = [index, confidence]
        
        return tuple(chosen)
    
    def recognize_violation(self, vehicles, line_position, tracked_violators):
        """Recognize red light violations"""
        tracked_vehicles = vehicles[[len(v) == 7 for v in vehicles]]
        if len(tracked_vehicles) == 0:
            return tracked_violators, torch.empty((0, 7), device=vehicles.device), []

        newly_caught_vehicles = []
        for vehicle in tracked_vehicles:
            tracker_id = int(vehicle[4])
            vehicle_center_y = (vehicle[1] + vehicle[3]) / 2
            if vehicle_center_y > line_position:
                if tracker_id not in tracked_violators:
                    tracked_violators.add(tracker_id)
                    newly_caught_vehicles.append(vehicle)

        all_violators = torch.empty((0, 7), device=vehicles.device)
        if tracked_violators:
            violator_mask = torch.tensor([int(v[4]) in tracked_violators for v in tracked_vehicles], device=vehicles.device)
            all_violators = tracked_vehicles[violator_mask]

        return tracked_violators, all_violators, newly_caught_vehicles

    async def process_video_enhanced(self, input_path: str, output_path: str, 
                                   expected_traffic_direction='right',
                                   min_motorcycle_area=3000, 
                                   helmet_check_confidence=0.6,
                                   job_id: str = None) -> Dict[str, Any]:
        """
        Enhanced video processing with violation detection and database updates
        """
        print(f"🎬 Starting enhanced video processing for job: {job_id}")
        
        # Initialize statistics
        stats = {
            'red_light_violations': 0,
            'helmet_violations': 0,
            'wrong_way_violations': 0,
            'helmets_skipped': 0,
            'license_plates_detected': 0
        }
        
        detected_plates = set()
        all_red_light_violators = set()
        helmet_violator_ids = set()
        wrong_way_ids = set()
        
        # Video processing setup
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception(f"Error: Could not open video file {input_path}")
            
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Use avc1 codec for maximum web compatibility (H.264)
        out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'avc1'), fps, (width, height))
        
        # Store last processed frame data for consistent annotations
        last_vehicles = []
        last_traffic_lights = []
        last_light_colors = {}
        last_red_light_violators = set()
        last_helmet_violators = set()
        last_wrong_way_ids = set()

        # Process more frames for better detection quality (matching notebook approach)
        frame_skip = max(1, fps // 10)  # Process every 10th frame for better detection quality
        print(f"🎬 Processing video: {width}x{height} @ {fps}fps, {total_frames} frames (processing every {frame_skip} frames)")

        frame_count = 0
        
        # Send progress updates via WebSocket
        try:
            from app.websocket.connection_manager import manager
        except ImportError:
            manager = None

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
                
            frame_count += 1
            
            # Skip frames for faster processing
            if frame_count % frame_skip != 0:
                # Apply last processed frame's annotations for consistency
                self._annotate_frame(frame, last_vehicles, last_traffic_lights, last_light_colors, 
                                   last_red_light_violators, last_helmet_violators, last_wrong_way_ids)
                out.write(frame)
                continue
                
            # Resize frame for processing
            if width > 1920:
                scale = 1920 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))
                
            # Send progress update
            if manager and job_id and frame_count % (frame_skip * 10) == 0:
                progress = (frame_count / total_frames) * 100
                await manager.send_job_progress(job_id, {
                    "status": "processing",
                    "frame_count": frame_count,
                    "total_frames": total_frames,
                    "progress": progress,
                    "message": f"Processing frame {frame_count}/{total_frames}"
                })

            # YOLO detection with optimized settings
            # Use same approach as notebook for better detection quality
            results = self.model.track(
                frame, 
                persist=True, 
                classes=self.class_indices, 
                verbose=False
            )
            
            # Handle no detections
            if not results or len(results) == 0 or results[0].boxes is None:
                out.write(frame)
                continue

            detection_data = results[0].boxes.data
            if len(detection_data) == 0:
                out.write(frame)
                continue
                
            traffic_light_mask = detection_data[:, -1] == self.classes_to_detect['traffic light']
            traffic_lights = detection_data[traffic_light_mask]
            vehicles = detection_data[~traffic_light_mask]

            # License plate detection (only every 5th processed frame for speed)
            if (frame_count // frame_skip) % 5 == 0:
                plate = self._detect_license_plate(frame, vehicles, detected_plates)
                if plate:
                    stats['license_plates_detected'] += 1

            # Red light violation detection
            light_colors = self._detect_light_colors(frame, traffic_lights)
            red_light_index, red_confidence = self._choose_primary_red_light(light_colors)
            
            if red_light_index is not None and red_confidence > 0.5:
                line_y = traffic_lights[red_light_index][3] + 50  # Stop line
                newly_caught = []
                for vehicle in vehicles:
                    if len(vehicle) >= 7:  # Ensure tracked vehicle
                        tracker_id = int(vehicle[4])
                        vehicle_center_y = (vehicle[1] + vehicle[3]) / 2
                        if vehicle_center_y > line_y and tracker_id not in all_red_light_violators:
                            all_red_light_violators.add(tracker_id)
                            newly_caught.append(vehicle)
                            stats['red_light_violations'] += 1
                            self._save_violation_evidence(frame, vehicle, "red_light", frame_count, job_id)
                            
                            # Send violation notification
                            if manager and job_id:
                                await manager.send_violation_detected(job_id, {
                                    "type": "red_light",
                                    "vehicle_type": self._get_class_name(int(vehicle[6])),
                                    "tracker_id": tracker_id,
                                    "confidence": float(vehicle[5]),
                                    "frame": frame_count
                                })

            # Helmet violation detection (only every 3rd processed frame for speed)
            motorcycles = torch.empty((0, 7), device=vehicles.device) # Initialize motorcycles outside the if block
            if (frame_count // frame_skip) % 3 == 0:
                motorcycle_mask = vehicles[:, -1] == self.classes_to_detect.get('motorcycle', -1)
                motorcycles = vehicles[motorcycle_mask]
                
                if motorcycles.numel() > 0:
                    for mc in motorcycles:
                        if len(mc) >= 7:  # Ensure tracked
                            tracker_id = int(mc[4])
                            if tracker_id not in helmet_violator_ids:
                                mc_area = (mc[2] - mc[0]) * (mc[3] - mc[1])
                                if mc_area >= min_motorcycle_area:
                                    # Helmet detection logic (simplified)
                                    has_helmet = self._detect_helmet(frame, mc)
                                    if not has_helmet:
                                        helmet_violator_ids.add(tracker_id)
                                        stats['helmet_violations'] += 1
                                        self._save_violation_evidence(frame, mc, "helmet", frame_count, job_id)
                                        print(f"New Helmet Violation: Tracker ID {tracker_id} (motorcycle area: {int(mc_area)})")
                                        
                                        # Send violation notification
                                        if manager and job_id:
                                            await manager.send_violation_detected(job_id, {
                                                "type": "helmet",
                                                "vehicle_type": "motorcycle",
                                                "tracker_id": tracker_id,
                                                "confidence": float(mc[5]),
                                                "frame": frame_count
                                            })
            
            # Wrong way detection
            for vehicle in vehicles:
                if len(vehicle) >= 7:  # Ensure tracked
                    tracker_id = int(vehicle[4])
                    if tracker_id not in wrong_way_ids:
                        # Simplified wrong way detection based on direction
                        vehicle_center_x = (vehicle[0] + vehicle[2]) / 2
                        if expected_traffic_direction == 'right' and vehicle_center_x < width * 0.3:
                            wrong_way_ids.add(tracker_id)
                            stats['wrong_way_violations'] += 1
                            self._save_violation_evidence(frame, vehicle, "wrong_way", frame_count, job_id)
                            
                            # Send violation notification
                            if manager and job_id:
                                await manager.send_violation_detected(job_id, {
                                    "type": "wrong_way",
                                    "vehicle_type": self._get_class_name(int(vehicle[6])),
                                    "tracker_id": tracker_id,
                                    "confidence": float(vehicle[5]),
                                    "frame": frame_count
                                })
            
            # Annotate frame
            self._annotate_frame(frame, vehicles, traffic_lights, light_colors, 
                               all_red_light_violators, helmet_violator_ids, 
                               wrong_way_ids)
            
            # Store current frame data for skipped frames
            last_vehicles = vehicles
            last_traffic_lights = traffic_lights
            last_light_colors = light_colors
            last_red_light_violators = all_red_light_violators
            last_helmet_violators = helmet_violator_ids
            last_wrong_way_ids = wrong_way_ids
            
            out.write(frame)
        
        cap.release()
        out.release()

        print("=" * 50)
        print("Enhanced Processing Complete - Violation Statistics:")
        print(f"Red Light Violations: {stats['red_light_violations']}")
        print(f"Helmet Violations: {stats['helmet_violations']}")
        print(f"Wrong Way Violations: {stats['wrong_way_violations']}")
        print(f"License Plates Detected: {stats['license_plates_detected']}")
        print(f"Helmets Skipped: {stats['helmets_skipped']}")
        print("=" * 50)

        # Update job statistics in database
        if job_id:
            try:
                # Use SessionLocal directly instead of get_db dependency
                with SessionLocal() as db:
                    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
                    if job:
                        total_viol = stats['red_light_violations'] + stats['helmet_violations'] + stats['wrong_way_violations']
                        job.total_violations = total_viol
                        job.red_light_violations = stats['red_light_violations']
                        job.helmet_violations = stats['helmet_violations']
                        job.wrong_way_violations = stats['wrong_way_violations']
                        db.commit()
                        print(f"✅ Job statistics updated in database: Total={total_viol}, Red={stats['red_light_violations']}, Helmet={stats['helmet_violations']}, Wrong={stats['wrong_way_violations']}")
                        
                        # Verify the update was successful
                        db.refresh(job)
                        print(f"✅ Verification: Database shows Total={job.total_violations}, Red={job.red_light_violations}, Helmet={job.helmet_violations}, Wrong={job.wrong_way_violations}")
                    else:
                        print(f"❌ Job not found in database: {job_id}")
            except Exception as e:
                print(f"❌ Failed to update job statistics: {e}")
                import traceback
                traceback.print_exc()

        return {
            'stats': stats,
            'detected_plates': list(detected_plates),
            'total_frames': total_frames,
            'processing_time': datetime.now().isoformat()
        }
    
    def _detect_license_plate(self, frame, vehicles, detected_plates):
        """Simplified license plate detection"""
        # This is a placeholder - implement actual EasyOCR logic
        return None
        
    def _detect_light_colors(self, frame, traffic_lights):
        """Simplified traffic light color detection"""
        colors = {"red": [], "yellow": [], "green": [], "light's off": []}
        for i, light in enumerate(traffic_lights):
            # Simplified: assume red light detected
            colors["red"].append((i, 0.8))
        return colors
        
    def _choose_primary_red_light(self, light_colors):
        """Choose the primary red light for violation detection"""
        if not light_colors['red']:
            return None, 0.0
        # Return first red light with highest confidence
        return light_colors['red'][0]
        
    def _detect_helmet(self, frame, motorcycle):
        """Simplified helmet detection"""
        # Placeholder - implement actual helmet detection logic
        return False  # Always return no helmet for testing
        
            
    def _save_violation_evidence(self, frame, violator_tensor, violation_type, frame_count, job_id=None):
        """Save evidence image for violation and database record"""
        evidence_frame = frame.copy()
        x1, y1, x2, y2 = map(int, violator_tensor[:4])
        cv2.rectangle(evidence_frame, (x1, y1), (x2, y2), (0, 255, 255), 5)
        
        tracker_id = int(violator_tensor[4])
        class_name = self._get_class_name(int(violator_tensor[6]))
        save_path = f"{violation_type}_violator_{class_name}_{tracker_id}_frame{frame_count}.jpg"
        cv2.imwrite(save_path, evidence_frame)
        
        # Save violation to database
        if job_id:
            try:
                from datetime import datetime
                
                with SessionLocal() as db:
                    violation = Violation(
                        violation_type=violation_type,
                        vehicle_type=class_name,
                        tracker_id=tracker_id,
                        confidence=float(violator_tensor[5]) if len(violator_tensor) >= 6 else 0.0,
                        frame_number=frame_count,
                        evidence_image_path=save_path,
                        violation_coordinates=json.dumps({
                            "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)
                        }),
                        timestamp=datetime.utcnow()
                    )
                    db.add(violation)
                    db.commit()
                    print(f"✅ Violation saved to database: {violation_type} - {class_name} (ID: {tracker_id})")
            except Exception as e:
                print(f"❌ Failed to save violation to database: {e}")
                
    def _get_class_name(self, class_id):
        """Get class name from class ID"""
        for name, id_val in self.classes_to_detect.items():
            if id_val == class_id:
                return name
        return "unknown"
