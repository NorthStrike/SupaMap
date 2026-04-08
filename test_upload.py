from core.media_handler import process_and_save_video_upload
import os

source = r"D:\SupaMap\project_data\videos\Video Test.MOV"
try:
    print("processing...")
    target_video_path, lat, lon, heading, timestamp_str = process_and_save_video_upload(source)
    print("Extracted to:", target_video_path)
except Exception as e:
    print("Error:", e)
