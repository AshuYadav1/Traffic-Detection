"""
PIL compatibility patch for newer versions of Pillow
This fixes the ANTIALIAS attribute issue in newer Pillow versions
"""

import PIL.Image

# Add ANTIALIAS attribute if it doesn't exist (for newer Pillow versions)
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# Also patch the Image module directly
if not hasattr(PIL.Image.Image, 'ANTIALIAS'):
    PIL.Image.Image.ANTIALIAS = PIL.Image.LANCZOS
