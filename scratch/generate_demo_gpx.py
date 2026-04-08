import os
import gpxpy.gpx
import math

BASE_LAT, BASE_LON = 44.82805, -76.51805
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GPX_DIR = os.path.join(PROJ_ROOT, "project_data", "gpx")

def create_gpx_line(category, points, closed=False):
    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    
    for pt in points:
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(pt[0], pt[1]))
    
    if closed and len(points) > 0:
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(points[0][0], points[0][1]))
    
    path = os.path.join(GPX_DIR, category, f"demo_{category}.gpx")
    with open(path, "w") as f:
        f.write(gpx.to_xml())

def main():
    # 1. Trail (Open line) - Slight spiral
    trail_pts = [(BASE_LAT + i*0.0001, BASE_LON + i*0.0002) for i in range(20)]
    create_gpx_line("trails", trail_pts)
    
    # 2. Cliff (Open line) - Jagged line
    cliff_pts = [
        (BASE_LAT + 0.002, BASE_LON + 0.001),
        (BASE_LAT + 0.0022, BASE_LON + 0.0012),
        (BASE_LAT + 0.002, BASE_LON + 0.0014),
        (BASE_LAT + 0.0025, BASE_LON + 0.0016)
    ]
    create_gpx_line("cliffs", cliff_pts)
    
    # 3. Pond (Closed loop)
    pond_pts = []
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        pond_pts.append((BASE_LAT - 0.001 + 0.0005 * math.sin(rad), BASE_LON - 0.001 + 0.0008 * math.cos(rad)))
    create_gpx_line("ponds", pond_pts, closed=True)
    
    # 4. Boundary (Closed loop - Square bounding)
    bound_pts = [
        (BASE_LAT - 0.004, BASE_LON - 0.004),
        (BASE_LAT + 0.004, BASE_LON - 0.004),
        (BASE_LAT + 0.004, BASE_LON + 0.004),
        (BASE_LAT - 0.004, BASE_LON + 0.004)
    ]
    create_gpx_line("boundaries", bound_pts, closed=True)
    
    print("Successfully generated 4 demo GPX files.")

if __name__ == "__main__":
    main()
