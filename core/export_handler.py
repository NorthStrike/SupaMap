import os
import csv
import sqlite3
import simplekml
from core.db_manager import DB_PATH, get_all_pois
from core.gpx_parser import load_all_gpx

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def export_csv(filepath: str):
    """
    Dumps all media POIs strictly targeting structured spreadsheet bindings.
    """
    pois = get_all_pois() # Pulls all bounds entirely unfiltered natively
    if not pois:
        return False
        
    keys = ['id', 'type', 'filepath', 'lat', 'lon', 'heading', 'timestamp', 'notes', 'rotation']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for p in pois:
            writer.writerow(p)
            
    return True

def export_kml(filepath: str):
    """
    Generates a Google Earth compliant File embedding entirely decoupled Vector geometries safely!
    """
    kml = simplekml.Kml(name="SupaMap Property Data")
    
    # 1. Parse all GPX Arrays natively tracking boundaries and paths
    gpx_dir = os.path.join(PROJ_ROOT, "project_data", "gpx")
    if os.path.exists(gpx_dir):
        parsed = load_all_gpx(gpx_dir)
        
        # Add Boundaries
        bnd_folder = kml.newfolder(name="Boundaries")
        for p in parsed.get('boundaries', []):
            coords = p['coords']
            if len(coords) > 2:
                poly = bnd_folder.newpolygon(name=p['name'], outerboundaryis=[(c[1], c[0]) for c in coords])
                poly.style.linestyle.color = simplekml.Color.red
                poly.style.linestyle.width = 3
                poly.style.polystyle.fill = 0
                
        # Add Ponds
        pond_folder = kml.newfolder(name="Ponds")
        for p in parsed.get('ponds', []):
            coords = p['coords']
            if len(coords) > 2:
                poly = pond_folder.newpolygon(name=p['name'], outerboundaryis=[(c[1], c[0]) for c in coords])
                poly.style.linestyle.color = simplekml.Color.blue
                poly.style.polystyle.color = simplekml.Color.changealphaint(100, simplekml.Color.aqua)
                
        # Add Trails
        trail_folder = kml.newfolder(name="Trails")
        for p in parsed.get('trails', []):
            coords = p['coords']
            line = trail_folder.newlinestring(name=p['name'], description=f"Length: {p['distance_2d']:.1f}m\\nGrade: {p.get('avg_grade',0):.1f}%")
            # KML inherently mandates standard geographic tuple ordering arrays explicitly structured natively (lon, lat, elev)
            line.coords = [(c[1], c[0], c[2] or 0.0) for c in coords]
            line.style.linestyle.color = simplekml.Color.green
            line.style.linestyle.width = 3
            
        # Add Cliffs
        cliff_folder = kml.newfolder(name="Cliffs")
        for p in parsed.get('cliffs', []):
            coords = p['coords']
            line = cliff_folder.newlinestring(name=p['name'])
            line.coords = [(c[1], c[0]) for c in coords]
            line.style.linestyle.color = simplekml.Color.brown
            line.style.linestyle.width = 4
            
    # 2. Extract SQLite Database Pins
    pois = get_all_pois()
    if pois:
        media_folder = kml.newfolder(name="Media Pins")
        for p in pois:
            if p['lat'] == 999.0:
                continue # Do not project Un-mapped missing media into Google Earth!
                
            filename = os.path.basename(p['filepath'])
            pnt = media_folder.newpoint(name=filename, coords=[(p['lon'], p['lat'])])
            pnt.description = f"Type: {p['type']}\\nTimestamp: {p['timestamp']}\\nHeading: {p['heading']}\\nNotes: {p['notes']}"
            
    kml.save(filepath)
    return True
