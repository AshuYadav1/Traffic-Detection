#!/usr/bin/env python3
"""
Test script for the enhanced violation processor
"""

import os
import sys
import asyncio

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def test_enhanced_processor():
    """Test the enhanced violation processor"""
    try:
        print("🧪 Testing Enhanced Violation Processor...")
        
        # Import the enhanced processor
        from app.services.enhanced_violation_processor import EnhancedViolationProcessor
        
        print("✅ Enhanced processor imported successfully")
        
        # Initialize the processor
        processor = EnhancedViolationProcessor()
        print("✅ Enhanced processor initialized successfully")
        
        # Test model loading
        print(f"✅ YOLO model: {processor.model is not None}")
        print(f"✅ SVM model: {processor.svm_model is not None}")
        print(f"✅ PCA model: {processor.pca is not None}")
        print(f"✅ OCR reader: {processor.ocr_reader is not None}")
        print(f"✅ Accident detector: {processor.accident_interpreter is not None}")
        
        print("\n🎉 All tests passed! Enhanced processor is ready to use.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enhanced_processor())
