import cv2
print("CV2 imported")
video_path = r"D:\SupaMap\project_data\videos\Video Test.MOV"
vidcap = cv2.VideoCapture(video_path)
print("Is opened:", vidcap.isOpened())
success, image = vidcap.read()
print("Success:", success)
if success:
    print("Shape:", image.shape)
