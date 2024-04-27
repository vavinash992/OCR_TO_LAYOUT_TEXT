import numpy as np
import cv2
import fitz  # PyMuPDF

import cv2
import fitz  # PyMuPDF
import numpy as np

def _get_image(file_path):
    # Determine the file type from the extension
    file_type = file_path.split('.')[-1].lower()
    
    if file_type in ['png', 'jpg', 'jpeg', 'gif']:
        # Read the image using OpenCV
        image = cv2.imread(file_path)
        if image is None:
            return None
        height, width = image.shape[:2]
        _, im_buf_arr = cv2.imencode(f".{file_type}", image)
        byte_img = im_buf_arr.tobytes()
        return [(byte_img, width, height)]  # Return as a list for consistency with PDF handling
    
    elif file_type == 'pdf':
        # Open the PDF file
        doc = fitz.open(file_path)
        images = []
        for page in doc:
            pix = page.get_pixmap()
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            height, width = img.shape[:2]
            _, im_buf_arr = cv2.imencode(".jpg", img)
            byte_img = im_buf_arr.tobytes()
            images.append((byte_img, width, height))
        doc.close()
        return images
    
    else:
        return None
