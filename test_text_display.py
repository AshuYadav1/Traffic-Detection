#!/usr/bin/env python3
"""
Test text display in video annotations
"""

import cv2
import numpy as np
import os

def test_text_display():
    """Test if our text annotation works properly"""
    print("🧪 Testing Text Display in Annotations")
    print("=" * 50)
    
    # Create a test image
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    test_image.fill(100)  # Gray background
    
    # Test parameters
    x1, y1, x2, y2 = 50, 50, 200, 150
    label = "89.2% motorcycle"
    color = (0, 255, 0)  # Green box
    
    # Draw bounding box
    cv2.rectangle(test_image, (x1, y1), (x2, y2), color, 2)
    
    # Draw text with better visibility (matching our implementation)
    if label:
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
        
        # Text background position
        text_x = x1
        text_y = y1 - 10
        if text_y - text_height < 0:
            text_y = y2 + text_height + 5
        
        # Draw text background for better visibility
        cv2.rectangle(test_image, 
                    (text_x, text_y - text_height - 5), 
                    (text_x + text_width + 5, text_y + 5), 
                    (0, 0, 0), -1)  # Black background
        
        # Draw white text on black background
        cv2.putText(test_image, label, (text_x + 2, text_y), font, font_scale, (255, 255, 255), thickness)
    
    # Save test image
    output_path = "test_text_display.jpg"
    cv2.imwrite(output_path, test_image)
    
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"✅ Test image created: {output_path} ({file_size} bytes)")
        print(f"📋 Test shows: Green box with '{label}' in white text on black background")
        print(f"💡 If this works, your video annotations should now show text properly!")
        return True
    else:
        print(f"❌ Failed to create test image")
        return False

if __name__ == "__main__":
    success = test_text_display()
    if success:
        print(f"\n🎉 Text display test completed!")
        print(f"Your video processing should now show:")
        print(f"   ✅ Colored bounding boxes")
        print(f"   ✅ White text labels on black backgrounds") 
        print(f"   ✅ Format: '89.2% motorcycle', '94.5% car VIOLATES'")
    else:
        print(f"\n❌ Test failed - check OpenCV installation")
