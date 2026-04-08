import shapely.geometry
from pyproj import Geod

def calculate_polygon_metrics(coords_2d):
    """
    Evaluates a closed sequence of [ (lat, lon) ... ] computing:
    - Total physical Geodesic Area in square meters & acres
    - Total physical Geodesic Perimeter in meters
    Returns: (area_sqm, area_acres, perimeter_m)
    """
    if len(coords_2d) < 3:
        return 0.0, 0.0, 0.0
        
    # Shapely utilizes (lon, lat) traditionally for x/y geometric bounds
    # Ensure polygon cleanly closes mathematically
    poly_coords = [(lon, lat) for (lat, lon) in coords_2d]
    if poly_coords[0] != poly_coords[-1]:
        poly_coords.append(poly_coords[0])
        
    poly = shapely.geometry.Polygon(poly_coords)
    
    # pyproj Geod algorithm constructs perfect physical ellipsoid projection math (WGS84)
    # Area computing drops directly into precision measurements scaling earth's curvature seamlessly
    geod = Geod(ellps="WGS84")
    
    # geod.geometry_area_perimeter accepts shapely polygons dynamically 
    area_sqm, perimeter_m = geod.geometry_area_perimeter(poly)
    
    # WGS84 outputs signed bounds depending on clockwise winding direction, force absolute constraints
    area_sqm = abs(area_sqm)
    
    # 1 Acre = 4046.8564224 square meters exactly
    area_acres = area_sqm / 4046.8564224
    
    return area_sqm, area_acres, perimeter_m

def calculate_line_of_sight(lat1, lon1, lat2, lon2):
    """
    Computes absolute true bearing and distances between two points mapping standard PyProj limits.
    Returns: (forward_azimuth_deg, distance_m, distance_ft)
    """
    geod = Geod(ellps="WGS84")
    # 'inv' measures Inverse Geodetic properties (Point A -> Point B)
    fwd_az, back_az, dist_m = geod.inv(lon1, lat1, lon2, lat2)
    
    # PyProj limits inverse azimuth bounds across -180 to 180 degrees.
    # Convert standard mapping limits wrapping strictly to 0 - 360 degrees mapping a 360 compass!
    bearing = (fwd_az + 360) % 360
    
    dist_ft = dist_m * 3.28084
    return bearing, dist_m, dist_ft
