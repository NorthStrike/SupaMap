import os
import shutil
from PIL import Image
import exifread

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _convert_to_degrees(value):
    """Converts the raw exifread IFDRatio object to a distinct float"""
    if not value or len(value.values) < 3:
         return 0.0
    d = float(value.values[0].num) / float(value.values[0].den)
    m = float(value.values[1].num) / float(value.values[1].den)
    s = float(value.values[2].num) / float(value.values[2].den)
    return d + (m / 60.0) + (s / 3600.0)

def extract_exif_gps(filepath):
    """
    Parses EXIF. Returns (lat, lon, heading) explicitly.
    Will gracefully omit heading if malformed. Returns (None, None, None) on global failure.
    """
    with open(filepath, 'rb') as f:
        tags = exifread.process_file(f, details=False)
        
        if 'GPS GPSLatitude' not in tags or 'GPS GPSLongitude' not in tags:
            return None, None, None
            
        lat = _convert_to_degrees(tags['GPS GPSLatitude'])
        lat_ref = tags.get('GPS GPSLatitudeRef')
        if lat_ref and lat_ref.values[0] != 'N':
            lat = -lat
            
        lon = _convert_to_degrees(tags['GPS GPSLongitude'])
        lon_ref = tags.get('GPS GPSLongitudeRef')
        if lon_ref and lon_ref.values[0] != 'E':
            lon = -lon
            
        heading = None
        try:
            if 'GPS GPSImgDirection' in tags:
                val = tags['GPS GPSImgDirection'].values[0]
                heading = float(val.num) / float(val.den)
        except Exception:
            heading = None # Malformed EXIF protection
            
        return lat, lon, heading

import datetime
from PIL import Image, ImageOps

def process_and_save_upload(source_filepath):
    """
    Copies original and exports a resized thumbnail targeting standard directories.
    Returns (thumbnail_path_rel, lat, lon, heading, timestamp_str).
    """
    import uuid
    base_filename = os.path.basename(source_filepath)
    # Generate a unique hash avoiding cross-clashing if uploading identical physical duplicate files
    uid = uuid.uuid4().hex[:8]
    filename = f"{uid}_{base_filename}"
    
    photos_dir = os.path.join(PROJ_ROOT, "project_data", "photos")
    thumbs_dir = os.path.join(PROJ_ROOT, "project_data", "thumbnails")
    
    # Permanent physical paths
    target_photo_path = os.path.join(photos_dir, filename)
    target_thumb_path = os.path.join(thumbs_dir, filename)
    
    # 1. Copy
    shutil.copy2(source_filepath, target_photo_path)
    
    # 2. Extract GPS
    lat, lon, heading = extract_exif_gps(target_photo_path)
    
    # Extract True Timestamp
    timestamp_str = None
    try:
        with open(target_photo_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            if 'EXIF DateTimeOriginal' in tags:
                timestamp_str = str(tags['EXIF DateTimeOriginal'])
    except:
        pass
        
    if not timestamp_str: # Fallback to file creation time
        dt = datetime.datetime.fromtimestamp(os.path.getmtime(target_photo_path))
        timestamp_str = dt.isoformat()
        
    if lat is None:
        pass # The UI layer should handle parsing rejection visually if needed.
        
    # 3. Handle Thumbnail
    img = Image.open(target_photo_path)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((150, 150))
    img.save(target_thumb_path, format="JPEG")
    img.close()
        
    return target_thumb_path, lat, lon, heading, timestamp_str

import re
from mutagen.mp4 import MP4

def extract_video_gps(filepath):
    """
    Parses QuickTime MOV/MP4 using ExifTool to find Phil Harvey GPS Coordinates.
    Returns (lat, lon, heading).
    """
    import exiftool
    import traceback
    try:
        with exiftool.ExifToolHelper() as et:
            metadata = et.get_metadata(filepath)[0]
            
            # Print Metadata dump for debugging exactly as requested
            print(f"\n========== VIDEO EXIFTOOL METADATA DUMP ({os.path.basename(filepath)}) ==========")
            for k, v in metadata.items():
                print(f"{k}: {v}")
            print("====================================================\n")
            
            # Fast check: ExifTool often computes float composite coordinates automatically
            lat = metadata.get('Composite:GPSLatitude')
            lon = metadata.get('Composite:GPSLongitude')
            if lat is not None and lon is not None:
                return float(lat), float(lon), None
                
            # Direct parse fallbacks
            coords_str = None
            if 'ItemList:GPSCoordinates' in metadata:
                coords_str = str(metadata['ItemList:GPSCoordinates'])
            elif 'Keys:GPSCoordinates' in metadata:
                coords_str = str(metadata['Keys:GPSCoordinates'])
            elif 'QuickTime:GPSCoordinates' in metadata:
                coords_str = str(metadata['QuickTime:GPSCoordinates'])
                
            if coords_str:
                # Handle "+44.8280-076.5180" or "+44.8280, -076.5180"
                match_comma = re.search(r'([-+]\d+\.\d+)\s*,\s*([-+]\d+\.\d+)', coords_str)
                if match_comma:
                    return float(match_comma.group(1)), float(match_comma.group(2)), None
                    
                match_iso = re.search(r'([-+]\d+\.\d+)([-+]\d+\.\d+)', coords_str)
                if match_iso:
                    return float(match_iso.group(1)), float(match_iso.group(2)), None
                    
    except FileNotFoundError:
        pass # Silently drop missing exiftool binaries avoiding terminal clutter
    except Exception as e:
        print("ExifTool exception:")
        import traceback
        traceback.print_exc()
        
    return None, None, None

def process_and_save_video_upload(source_filepath):
    """
    Copies video and returns properties scaled identical to photos omitting thumbnailing.
    """
    import uuid
    base_filename = os.path.basename(source_filepath)
    uid = uuid.uuid4().hex[:8]
    filename = f"{uid}_{base_filename}"
    
    videos_dir = os.path.join(PROJ_ROOT, "project_data", "videos")
    
    target_video_path = os.path.join(videos_dir, filename)
    shutil.copy2(source_filepath, target_video_path)
    
    # Generate Thumbnail tracking physical OS limits
    thumbnails_dir = os.path.join(PROJ_ROOT, "project_data", "thumbnails")
    target_thumb_path = os.path.join(thumbnails_dir, filename + ".jpg")
    try:
        import cv2
        vidcap = cv2.VideoCapture(target_video_path)
        success, image = vidcap.read()
        if success:
            # Extract central square accurately before scaling matching photo bounding visually
            h, w = image.shape[:2]
            min_dim = min(h, w)
            sy, sx = (h - min_dim) // 2, (w - min_dim) // 2
            cropped = image[sy:sy+min_dim, sx:sx+min_dim]
            img_resized = cv2.resize(cropped, (150, 150), interpolation=cv2.INTER_AREA)
            cv2.imwrite(target_thumb_path, img_resized)
        vidcap.release()
    except Exception as e:
        print(f"Failed extracting native thumbnail cleanly: {e}")
        
    lat, lon, heading = extract_video_gps(target_video_path)
    
    dt = datetime.datetime.fromtimestamp(os.path.getmtime(target_video_path))
    timestamp_str = dt.isoformat()
    
    return target_video_path, lat, lon, heading, timestamp_str
