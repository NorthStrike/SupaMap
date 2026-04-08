import os
import gpxpy

def load_all_gpx(gpx_base_dir: str) -> dict:
    """
    Scans the specific category subfolders under project_data/gpx/
    and extracts PolyLine coordinate pairs.
    Returns: dict mapping category -> list of lines/polygons
             e.g., {'trails': [[(lat, lon), (lat, lon)], ...]}
    """
    categories = ['trails', 'ponds', 'cliffs', 'boundaries']
    parsed_data = {cat: [] for cat in categories}
    
    for category in categories:
        cat_dir = os.path.join(gpx_base_dir, category)
        if not os.path.exists(cat_dir):
            continue
            
        for filename in os.listdir(cat_dir):
            if filename.lower().endswith('.gpx'):
                filepath = os.path.join(cat_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        gpx = gpxpy.parse(f)
                        
                        for track in gpx.tracks:
                            for segment in track.segments:
                                coords = [(pt.latitude, pt.longitude, pt.elevation) for pt in segment.points]
                                if coords:
                                    import math
                                    is_poly = False
                                    if len(coords) > 2:
                                        d_lat = coords[0][0] - coords[-1][0]
                                        d_lon = coords[0][1] - coords[-1][1]
                                        if math.hypot(d_lat, d_lon) < 0.0001:
                                            is_poly = True
                                            
                                    area_sqm, area_acres, perimeter_m = 0.0, 0.0, 0.0
                                    if is_poly:
                                        from core.geometry import calculate_polygon_metrics
                                        area_sqm, area_acres, perimeter_m = calculate_polygon_metrics([(c[0], c[1]) for c in coords])
                                        
                                    elevations = [c[2] for c in coords if c[2] is not None]
                                    
                                    max_grade = 0.0
                                    total_elev_change = 0.0
                                    valid_dist = 0.0
                                    
                                    if len(segment.points) > 1:
                                        for i in range(1, len(segment.points)):
                                            p1, p2 = segment.points[i-1], segment.points[i]
                                            if p1.elevation is not None and p2.elevation is not None:
                                                dist = p1.distance_2d(p2)
                                                if dist and dist > 0:
                                                    elev_diff = abs(p2.elevation - p1.elevation)
                                                    grade = (elev_diff / dist) * 100.0
                                                    max_grade = max(max_grade, grade)
                                                    total_elev_change += elev_diff
                                                    valid_dist += dist
                                                    
                                    avg_grade = (total_elev_change / valid_dist * 100.0) if valid_dist > 0 else 0.0
                                    
                                    parsed_data[category].append({
                                        'coords': coords,
                                        'filepath': filepath,
                                        'name': os.path.splitext(filename)[0].replace('_', ' ').title(),
                                        'is_polygon': is_poly,
                                        'area_sqm': area_sqm,
                                        'area_acres': area_acres,
                                        'perimeter_m': perimeter_m,
                                        'min_ele': min(elevations) if elevations else None,
                                        'max_ele': max(elevations) if elevations else None,
                                        'distance_2d': segment.length_2d(),
                                        'max_grade': max_grade,
                                        'avg_grade': avg_grade
                                    })
                except Exception as e:
                    print(f"Failed to parse {filepath}: {e}")
                    
    return parsed_data
