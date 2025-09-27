"""
Minimal Enhanced Traffic Violation Detection Processor
Based on New21.ipynb with core features:
- License plate detection with EasyOCR
- Enhanced helmet detection (without SHAP for now)
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

from app.core.config import settings
from app.core.database import Violation, ProcessingJob, SessionLocal

class MinimalEnhancedProcessor:
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
        
        self._load_models()
        self._load_config()
        self._initialize_new_components()
    
    def _load_models(self):
        """Load YOLO, SVM, and PCA models"""
        try:
            # Load YOLO model
            model_path = settings.YOLO_MODEL_PATH
            if not os.path.exists(model_path):
                self._download_yolo_model()
            self.model = YOLO(model_path)
            print(f"✅ YOLO model loaded from {model_path}")
            
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
    
    # --- Enhanced Helmet Detection ---
    def predict_helmet_on_image_array(self, image, min_region_area=50, threshold=-0.1,
                                     motorcycle_box_size=None, min_box_area=5000):
        """Enhanced helmet prediction"""
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
                                   helmet_check_confidence=0.6) -> Dict[str, Any]:
        """
        Enhanced video processing with all new features
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found at {input_path}")

        # Initialize detectors
        wrong_way_detector = self.WrongWayDetector(history_length=15, min_displacement=40)
        wrong_way_detector.set_expected_direction(expected_traffic_direction)

        # Setup video processing
        cap = cv2.VideoCapture(input_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

        # Initialize tracking variables
        line_height_stats = {'n': 0, 'sum': 0, 'mean': 0}
        red_light_violator_ids = set()
        helmet_violator_ids = set()
        detected_plates = set()
        frame_count = 0

        stats = {
            'red_light_violations': 0,
            'helmet_violations': 0,
            'wrong_way_violations': 0,
            'helmets_skipped': 0,
            'license_plates_detected': 0
        }

        print(f"🎬 Processing video: {width}x{height} @ {fps}fps, {total_frames} frames")

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
                
            frame_count += 1
            if frame.shape[0] != height or frame.shape[1] != width:
                frame = cv2.resize(frame, (width, height))

            # YOLO detection
            results = self.model.track(frame, persist=True, classes=self.class_indices, verbose=False)
            if results[0].boxes is None or len(results[0].boxes) == 0:
                out.write(frame)
                continue

            detection_data = results[0].boxes.data
            traffic_light_mask = detection_data[:, -1] == self.classes_to_detect['traffic light']
            traffic_lights = detection_data[traffic_light_mask]
            vehicles = detection_data[~traffic_light_mask]

            # License plate detection
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
                        self._save_violation_evidence(frame, violator_tensor, "red_light", frame_count)

            # Helmet violation detection
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
                            self._save_violation_evidence(frame, mc, "helmet", frame_count)

            # Wrong way detection
            wrong_way_ids, newly_detected_wrong_way = wrong_way_detector.update_and_check(
                vehicles, width, height
            )
            
            if newly_detected_wrong_way:
                stats['wrong_way_violations'] += len(newly_detected_wrong_way)
                for wrong_way_id in newly_detected_wrong_way:
                    for v in vehicles:
                        if len(v) >= 7 and int(v[4]) == wrong_way_id:
                            self._save_violation_evidence(frame, v, "wrong_way", frame_count)
                            break

            # Annotate frame
            self._annotate_frame(frame, vehicles, traffic_lights, light_colors, 
                               all_red_light_violators, helmet_violator_ids, 
                               wrong_way_ids)
            
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

        return {
            'stats': stats,
            'detected_plates': list(detected_plates),
            'total_frames': total_frames,
            'processing_time': datetime.now().isoformat()
        }
    
    # --- Helper Methods ---
    def _save_violation_evidence(self, frame, violator_tensor, violation_type, frame_count):
        """Save evidence image for violation"""
        evidence_frame = frame.copy()
        x1, y1, x2, y2 = map(int, violator_tensor[:4])
        cv2.rectangle(evidence_frame, (x1, y1), (x2, y2), (0, 255, 255), 5)
        
        tracker_id = int(violator_tensor[4])
        class_name = self._get_class_name(int(violator_tensor[6]))
        save_path = f"{violation_type}_violator_{class_name}_{tracker_id}_frame{frame_count}.jpg"
        cv2.imwrite(save_path, evidence_frame)
    
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
            
            # Check for violations
            if tracker_id in red_light_violators:
                label = f"{tracker_id} {conf:.1f}% {class_name} VIOLATES"
                color = (0, 0, 255)  # Red
            elif tracker_id in helmet_violators:
                label = f"{tracker_id} {conf:.1f}% {class_name} NO HELMET"
                color = (0, 255, 255)  # Yellow
            elif tracker_id in wrong_way_ids:
                label = f"{tracker_id} {conf:.1f}% {class_name} WRONG WAY"
                color = (255, 0, 255)  # Magenta
            else:
                label = f"{tracker_id} {conf:.1f}% {class_name}" if tracker_id else f"{conf:.1f}% {class_name}"
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
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
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
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
