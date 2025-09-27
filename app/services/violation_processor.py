"""
Traffic Violation Detection Processor
Converts the Jupyter notebook logic into a service class
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
import requests

from app.core.config import settings
from app.core.database import Violation, ProcessingJob, SessionLocal

class ViolationProcessor:
    def __init__(self):
        self.model = None
        self.svm_model = None
        self.pca = None
        self.config = None
        self.classes_to_detect = {}
        self.class_indices = []
        self.colors = {}
        self.palettes = {}
        
        self._load_models()
        self._load_config()
    
    def _load_models(self):
        """Load YOLO, SVM, and PCA models"""
        try:
            # Load YOLO model
            model_path = settings.YOLO_MODEL_PATH
            if not os.path.exists(model_path):
                # Download if not exists
                self._download_yolo_model()
            self.model = YOLO(model_path)
            print(f"✅ YOLO model loaded from {model_path}")
            
            # Load SVM and PCA models
            if os.path.exists(settings.SVM_MODEL_PATH):
                self.svm_model = joblib.load(settings.SVM_MODEL_PATH)
                print(f"✅ SVM model loaded from {settings.SVM_MODEL_PATH}")
            else:
                print(f"⚠️ SVM model not found at {settings.SVM_MODEL_PATH}")
                
            if os.path.exists(settings.PCA_MODEL_PATH):
                self.pca = joblib.load(settings.PCA_MODEL_PATH)
                print(f"✅ PCA model loaded from {settings.PCA_MODEL_PATH}")
            else:
                print(f"⚠️ PCA model not found at {settings.PCA_MODEL_PATH}")
                
        except Exception as e:
            print(f"❌ Error loading models: {e}")
            raise
    
    def _download_yolo_model(self):
        """Download YOLO model if not present"""
        import requests
        model_url = "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt"
        os.makedirs(os.path.dirname(settings.YOLO_MODEL_PATH), exist_ok=True)
        
        print(f"📥 Downloading YOLO model from {model_url}")
        response = requests.get(model_url)
        with open(settings.YOLO_MODEL_PATH, 'wb') as f:
            f.write(response.content)
        print(f"✅ YOLO model downloaded to {settings.YOLO_MODEL_PATH}")
    
    def _load_config(self):
        """Load configuration from YAML or use defaults"""
        config_path = "config.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            # Use default config
            self.config = {
                'object_classes': {
                    'car': 2, 'motorcycle': 3, 'bus': 5, 'truck': 7, 'traffic light': 9
                },
                'color_pallete': {
                    'red': [0, 0, 255], 'amber': [0, 191, 255], 'lime': [0, 255, 0],
                    'emerald': [80, 200, 120], 'cyan': [255, 255, 0], 'blue': [255, 0, 0],
                    'violet': [226, 43, 138], 'fuchsia': [255, 0, 255], 'rose': [255, 0, 127]
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
    
    # Image preprocessing functions (from notebook)
    def preprocess_image(self, image, target_size=(256, 256)):
        """Preprocess image for better detection"""
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
        """Segment image using Canny edge detection"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, low_threshold, high_threshold)
        kernel = np.ones((5,5), np.uint8)
        morph = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        return morph
    
    def extract_hog_features(self, image):
        """Extract HOG features from image"""
        try:
            from skimage.feature import hog
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            features, hog_image = hog(gray,
                                    orientations=9,
                                    pixels_per_cell=(8,8),
                                    cells_per_block=(2,2),
                                    visualize=True)
            return features
        except ImportError:
            # Fallback if scikit-image is not available
            print("Warning: scikit-image not available, using basic features")
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            # Return basic features as fallback
            return np.histogram(gray.ravel(), bins=256)[0].astype(np.float32)
    
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
    
    def predict_helmet_on_image_array(self, image, min_region_area=50, threshold=-0.1,
                                    motorcycle_box_size=None, min_box_area=5000):
        """Enhanced helmet prediction with size filtering"""
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
        
        if self.svm_model is None or self.pca is None:
            return {"final_prediction": "Model not available", "scores": [], "skipped": True}
        
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
        
        features_reduced = self.pca.transform(features_array)
        scores = self.svm_model.decision_function(features_reduced)
        
        preds = (scores >= threshold).astype(int)
        final_label = "Helmet" if np.any(preds == 1) else "No Helmet"
        
        results = []
        for i, score in enumerate(scores):
            pred_label = "Helmet" if preds[i] == 1 else "No Helmet"
            results.append({
                "region_index": i+1,
                "score": float(score),
                "prediction": pred_label
            })
        
        return {
            "final_prediction": final_label,
            "scores": results,
            "skipped": False
        }
    
    def recognize_traffic_light_color(self, frame, predictions):
        """Recognize traffic light colors"""
        colors = {'red': [], 'yellow': [], 'green': [], "light's off": []}
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        for i, traffic_light in enumerate(predictions):
            x1, y1, x2, y2 = map(int, traffic_light[:4])
            confidence = round(float(traffic_light[-2] * 100), 2)
            traffic_light_area = hsv_frame[y1:y2, x1:x2]
            
            if traffic_light_area.size == 0:
                continue
                
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
    
    def get_class_name(self, class_id):
        """Get class name from class ID"""
        try:
            return list(self.classes_to_detect.keys())[list(self.classes_to_detect.values()).index(class_id)]
        except ValueError:
            return "Unknown"
    
    def get_label_color(self, label):
        """Get color for label"""
        return self.palettes.get(label, (255, 255, 255))
    
    def current_color(self, box_index, recognized_colors):
        """Get current color for traffic light"""
        for color, boxes in recognized_colors.items():
            for data in boxes:
                if data[0] == box_index:
                    return color
        return "light's off"
    
    def annotate_frame(self, frame, prediction, recognized_colors={}, violation_mode=False, 
                      scale=0.5, padding=6, violation_text="VIOLATES"):
        """Annotate frame with detection results"""
        for i, row in enumerate(prediction):
            x1, y1, x2, y2 = map(int, row[:4])
            has_tracker_id = len(row) == 7
            if has_tracker_id:
                tracker_id, conf, class_id = int(row[4]), row[5] * 100, int(row[6])
            else:
                tracker_id, conf, class_id = None, row[4] * 100, int(row[5])
            
            class_name = self.get_class_name(class_id)
            if class_name == 'traffic light':
                color_name = self.current_color(i, recognized_colors)
                label, color = f'{conf:.2f}% {color_name.upper()}', self.get_label_color(color_name)
            elif violation_mode:
                label, color = f'{conf:.2f}% {class_name.title()} {violation_text}', self.get_label_color('red')
            else:
                label_id_str = str(tracker_id) if tracker_id is not None else ''
                label, color = f'{label_id_str} {conf:.2f}% {class_name.title()}', self.get_label_color(class_name)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, padding // 3)
            w_label, h_label = cv2.getTextSize(label, 0, scale, int(scale * 2))[0]
            cv2.rectangle(frame, (x1, y1 - h_label - 2 * padding), (x1 + w_label + 2 * padding, y1), color, -1)
            cv2.putText(frame, label, (x1 + padding, y1 - padding), 0, scale, (0, 0, 0), int(scale * 2), 16)
    
    async def process_video(self, input_path: str, output_path: str, job_id: str, 
                          expected_traffic_direction: str = "right",
                          min_motorcycle_area: int = 3000, 
                          helmet_check_confidence: float = 0.6,
                          progress_callback=None):
        """
        Process video with enhanced violation detection
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found at {input_path}")
        
        # Initialize database session
        db = SessionLocal()
        
        try:
            # Create evidence directory for this job
            job_evidence_dir = os.path.join(settings.EVIDENCE_DIR, job_id)
            os.makedirs(job_evidence_dir, exist_ok=True)
            
            # Open video
            cap = cv2.VideoCapture(input_path)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Setup video writer with web-compatible codec
            fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 codec for web compatibility
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # Check if the codec is supported, fallback to mp4v if not
            if not out.isOpened():
                print("⚠️ avc1 codec not supported, falling back to mp4v")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # Initialize tracking variables
            line_height_stats = {'n': 0, 'sum': 0, 'mean': 0}
            red_light_violator_ids = set()
            helmet_violator_ids = set()
            wrong_way_violator_ids = set()
            frame_count = 0
            
            # Initialize wrong way detector
            wrong_way_detector = WrongWayDetector(history_length=15, min_displacement=40)
            wrong_way_detector.set_expected_direction(expected_traffic_direction)
            
            # Track statistics
            stats = {
                'red_light_violations': 0,
                'helmet_violations': 0,
                'wrong_way_violations': 0,
                'helmets_skipped': 0
            }
            
            # Process frames
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    break
                    
                frame_count += 1
                
                # Resize frame if needed
                if frame.shape[0] != height or frame.shape[1] != width:
                    frame = cv2.resize(frame, (width, height))
                
                # Run YOLO detection
                results = self.model.track(frame, persist=True, classes=self.class_indices, verbose=False)
                
                if results[0].boxes is None or len(results[0].boxes) == 0:
                    out.write(frame)
                    if progress_callback:
                        await progress_callback(frame_count, total_frames, stats)
                    continue
                
                detection_data = results[0].boxes.data
                traffic_light_mask = detection_data[:, -1] == self.classes_to_detect['traffic light']
                traffic_lights = detection_data[traffic_light_mask]
                vehicles = detection_data[~traffic_light_mask]
                
                # Red Light Violation Detection
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
                    
                    # Check for red light violations
                    red_light_violator_ids, all_red_light_violators, newly_caught_red_light = self.recognize_violation(
                        vehicles, line_position, red_light_violator_ids
                    )
                    
                    if newly_caught_red_light:
                        stats['red_light_violations'] += len(newly_caught_red_light)
                        for violator_tensor in newly_caught_red_light:
                            await self._save_violation_evidence(
                                frame, violator_tensor, vehicles, traffic_lights, 
                                light_colors, all_red_light_violators, job_evidence_dir,
                                frame_count, "red_light", job_id, db
                            )
                    
                    # Draw violation line
                    cv2.line(frame, (0, round(line_position)), (frame.shape[1], round(line_position)), (0, 0, 255), 2)
                
                # Helmet Violation Detection
                motorcycle_mask = vehicles[:, -1] == self.classes_to_detect.get('motorcycle', -1)
                motorcycles = vehicles[motorcycle_mask]
                
                if motorcycles.numel() > 0:
                    for mc in motorcycles:
                        tracker_id = int(mc[4])
                        if tracker_id in helmet_violator_ids:
                            continue
                        
                        x1, y1, x2, y2 = map(int, mc[:4])
                        mc_width = x2 - x1
                        mc_height = y2 - y1
                        mc_area = mc_width * mc_height
                        
                        # Skip if motorcycle is too small
                        if mc_area < min_motorcycle_area:
                            stats['helmets_skipped'] += 1
                            continue
                        
                        # Extract helmet ROI
                        expansion_factor = 0.6
                        desired_height = int(mc_height * expansion_factor)
                        new_y1 = max(0, y1 - desired_height)
                        new_y2 = min(y1 + int(mc_height * 0.3), frame.shape[0])
                        
                        horizontal_expansion = int(mc_width * 0.1)
                        new_x1 = max(0, x1 - horizontal_expansion)
                        new_x2 = min(x2 + horizontal_expansion, frame.shape[1])
                        
                        helmet_roi = frame[new_y1:new_y2, new_x1:new_x2]
                        
                        if helmet_roi.size > 0:
                            helmet_result = self.predict_helmet_on_image_array(
                                helmet_roi, motorcycle_box_size=(mc_width, mc_height),
                                min_box_area=min_motorcycle_area
                            )
                            
                            if not helmet_result.get('skipped', False) and helmet_result['final_prediction'] == "No Helmet":
                                helmet_violator_ids.add(tracker_id)
                                stats['helmet_violations'] += 1
                                
                                await self._save_violation_evidence(
                                    frame, mc, vehicles, traffic_lights, 
                                    light_colors, all_red_light_violators, job_evidence_dir,
                                    frame_count, "helmet", job_id, db, mc
                                )
                
                # Wrong Way Detection
                wrong_way_ids, newly_detected_wrong_way = wrong_way_detector.update_and_check(
                    vehicles, width, height
                )
                
                if newly_detected_wrong_way:
                    stats['wrong_way_violations'] += len(newly_detected_wrong_way)
                    for wrong_way_id in newly_detected_wrong_way:
                        for v in vehicles:
                            if len(v) >= 7 and int(v[4]) == wrong_way_id:
                                await self._save_violation_evidence(
                                    frame, v, vehicles, traffic_lights, 
                                    light_colors, all_red_light_violators, job_evidence_dir,
                                    frame_count, "wrong_way", job_id, db
                                )
                                break
                
                # Annotate final frame
                self.annotate_frame(frame, vehicles)
                self.annotate_frame(frame, traffic_lights, recognized_colors=light_colors)
                
                if all_red_light_violators.numel() > 0:
                    self.annotate_frame(frame, all_red_light_violators, violation_mode=True)
                
                if helmet_violator_ids:
                    visible_helmet_violator_mask = torch.tensor([int(v[4]) in helmet_violator_ids for v in vehicles], device=vehicles.device)
                    all_helmet_violators = vehicles[visible_helmet_violator_mask]
                    if all_helmet_violators.numel() > 0:
                        self.annotate_frame(frame, all_helmet_violators, violation_mode=True, violation_text="NO HELMET")
                
                if wrong_way_ids:
                    visible_wrong_way_mask = torch.tensor([int(v[4]) in wrong_way_ids for v in vehicles if len(v) >= 7], device=vehicles.device)
                    wrong_way_vehicles = vehicles[[len(v) == 7 for v in vehicles]][visible_wrong_way_mask]
                    if wrong_way_vehicles.numel() > 0:
                        self.annotate_frame(frame, wrong_way_vehicles, violation_mode=True, violation_text="WRONG WAY")
                
                out.write(frame)
                
                if progress_callback:
                    await progress_callback(frame_count, total_frames, stats)
            
            # Cleanup
            cap.release()
            out.release()
            
            # Update job statistics
            total_violations = stats['red_light_violations'] + stats['helmet_violations'] + stats['wrong_way_violations']
            
            job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
            if job:
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.total_violations = total_violations
                job.red_light_violations = stats['red_light_violations']
                job.helmet_violations = stats['helmet_violations']
                job.wrong_way_violations = stats['wrong_way_violations']
                db.commit()
            
            return {
                "status": "completed",
                "total_violations": total_violations,
                "red_light_violations": stats['red_light_violations'],
                "helmet_violations": stats['helmet_violations'],
                "wrong_way_violations": stats['wrong_way_violations'],
                "helmets_skipped": stats['helmets_skipped']
            }
            
        except Exception as e:
            # Update job status to failed
            job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                db.commit()
            raise
        finally:
            db.close()
    
    async def _save_violation_evidence(self, frame, violator_tensor, vehicles, traffic_lights, 
                                     light_colors, all_red_light_violators, job_evidence_dir,
                                     frame_count, violation_type, job_id, db, motorcycle_tensor=None):
        """Save violation evidence image"""
        evidence_frame = frame.copy()
        self.annotate_frame(evidence_frame, vehicles)
        self.annotate_frame(evidence_frame, traffic_lights, recognized_colors=light_colors)
        
        if all_red_light_violators.numel() > 0:
            self.annotate_frame(evidence_frame, all_red_light_violators, violation_mode=True)
        
        x1, y1, x2, y2 = map(int, violator_tensor[:4])
        cv2.rectangle(evidence_frame, (x1, y1), (x2, y2), (0, 255, 255), 5)
        
        # Add motorcycle-specific annotations for helmet violations
        if violation_type == "helmet" and motorcycle_tensor is not None:
            self.annotate_frame(evidence_frame, motorcycle_tensor.unsqueeze(0), violation_mode=True, violation_text="NO HELMET")
        
        # Save evidence image
        tracker_id = int(violator_tensor[4]) if len(violator_tensor) >= 7 else 0
        class_name = self.get_class_name(int(violator_tensor[6]))
        evidence_filename = f'{violation_type}_violator_{class_name}_{tracker_id}_frame{frame_count}.jpg'
        evidence_path = os.path.join(job_evidence_dir, evidence_filename)
        cv2.imwrite(evidence_path, evidence_frame)
        
        # Save violation to database
        violation = Violation(
            violation_type=violation_type,
            vehicle_type=class_name,
            tracker_id=tracker_id,
            confidence=float(violator_tensor[5]) if len(violator_tensor) >= 6 else 0.0,
            frame_number=frame_count,
            evidence_image_path=evidence_path,
            violation_coordinates=json.dumps({
                "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)
            }),
            job_id=job_id
        )
        db.add(violation)
        db.commit()
    
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


class WrongWayDetector:
    """Wrong way detection class"""
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

# Create global instance
violation_processor = ViolationProcessor()
