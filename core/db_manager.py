import sqlite3
import os

from core.system_paths import get_install_dir
PROJ_ROOT = get_install_dir()
DB_PATH = os.path.join(PROJ_ROOT, "data", "app_state.sqlite")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media_pois (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            filepath TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            heading REAL,
            timestamp TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            lat1 REAL NOT NULL,
            lon1 REAL NOT NULL,
            lat2 REAL NOT NULL,
            lon2 REAL NOT NULL,
            distance_m REAL,
            bearing_deg REAL,
            timestamp TEXT
        )
    ''')
    
    # Workspace Location Management limits
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            center_lat REAL NOT NULL,
            center_lon REAL NOT NULL
        )
    ''')
    
    # Region Polygon Tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER DEFAULT 1,
            name TEXT NOT NULL,
            coords_json TEXT NOT NULL,
            acres REAL
        )
    ''')
    
    # Safe alteration for existing files
    try:
        cursor.execute('ALTER TABLE media_pois ADD COLUMN notes TEXT')
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute('ALTER TABLE media_pois ADD COLUMN rotation INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute('ALTER TABLE media_pois ADD COLUMN location_id INTEGER DEFAULT 1')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE measurements ADD COLUMN location_id INTEGER DEFAULT 1')
    except sqlite3.OperationalError:
        pass

    # Seed Default Home location
    cursor.execute('SELECT COUNT(*) FROM locations')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO locations (name, center_lat, center_lon) VALUES ('Home', 44.82702, -76.51533)")
        
    conn.commit()
    conn.close()

def get_all_locations():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, center_lat, center_lon FROM locations ORDER BY id ASC')
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "lat": r[2], "lon": r[3]} for r in rows]

def get_location(loc_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, center_lat, center_lon FROM locations WHERE id = ?', (loc_id,))
    r = cursor.fetchone()
    conn.close()
    return {"id": r[0], "name": r[1], "lat": r[2], "lon": r[3]} if r else None

def insert_location(name: str, lat: float, lon: float):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO locations (name, center_lat, center_lon) VALUES (?, ?, ?)', (name, lat, lon))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def delete_location(loc_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM media_pois WHERE location_id = ?', (loc_id,))
    cursor.execute('DELETE FROM measurements WHERE location_id = ?', (loc_id,))
    cursor.execute('DELETE FROM regions WHERE location_id = ?', (loc_id,))
    cursor.execute('DELETE FROM locations WHERE id = ?', (loc_id,))
    conn.commit()
    conn.close()

def insert_region(name: str, coords_json: str, acres: float, location_id: int = 1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO regions (name, coords_json, acres, location_id)
        VALUES (?, ?, ?, ?)
    ''', (name, coords_json, acres, location_id))
    rid = cursor.lastrowid
    conn.commit()
    conn.close()
    return rid

def get_all_regions(location_id: int = 1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, coords_json, acres FROM regions WHERE location_id = ? ORDER BY id ASC', (location_id,))
    rows = cursor.fetchall()
    conn.close()
    
    import json
    return [{"id": r[0], "name": r[1], "coords": json.loads(r[2]), "acres": r[3]} for r in rows]

def delete_region(region_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM regions WHERE id = ?', (region_id,))
    conn.commit()
    conn.close()

def insert_poi(poi_type: str, filepath: str, lat: float, lon: float, heading: float = None, timestamp: str = None, location_id: int = 1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO media_pois (type, filepath, lat, lon, heading, timestamp, location_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (poi_type, filepath, lat, lon, heading, timestamp, location_id))
    poi_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return poi_id

def update_note(poi_id: int, note: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE media_pois SET notes = ? WHERE id = ?', (note, poi_id))
    conn.commit()
    conn.close()

def get_poi_rotation(poi_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT rotation FROM media_pois WHERE id = ?', (poi_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] is not None:
        return row[0]
    return 0

def update_poi_rotation(poi_id: int, new_rot: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE media_pois SET rotation = ? WHERE id = ?', (new_rot, poi_id))
    conn.commit()
    conn.close()

def get_all_pois(location_id: int = 1, start_date=None, end_date=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = 'SELECT id, type, filepath, lat, lon, heading, timestamp, notes, rotation FROM media_pois WHERE location_id = ?'
    params = [location_id]
    
    if start_date and end_date:
        query += ' AND timestamp >= ? AND timestamp <= ?'
        params.extend([start_date, end_date])
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Pack to dict
    pois = []
    for r in rows:
        pois.append({
            'id': r[0],
            'type': r[1],
            'filepath': r[2],
            'lat': r[3],
            'lon': r[4],
            'heading': r[5],
            'timestamp': r[6],
            'notes': r[7] if r[7] else "",
            'rotation': r[8] if r[8] is not None else 0
        })
    return pois

def get_poi(poi_id: int):
    """Returns a singular POI dictionary matching explicitly to an ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, type, filepath, lat, lon FROM media_pois WHERE id = ?', (poi_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'type': row[1],
            'filepath': row[2],
            'lat': row[3],
            'lon': row[4]
        }
    return None

def delete_poi(poi_id: int):
    """Permanently drops exactly one physical record from the SQLite store."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM media_pois WHERE id = ?', (poi_id,))
    conn.commit()
    conn.close()

def fetch_media_stats(location_id: int = 1, start_date=None, end_date=None):
    """Returns absolute photo/video counts bounded natively within timestamps using >="""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT type, COUNT(*) FROM media_pois WHERE location_id = ?"
    params = [location_id]
    if start_date and end_date:
        query += " AND timestamp >= ? AND timestamp <= ?"
        params.extend([start_date, end_date])
        
    query += " GROUP BY type"
    cursor.execute(query, params)
    results = dict(cursor.fetchall())
    conn.close()
    
    return {
        'photos': results.get('photo', 0),
        'videos': results.get('video', 0)
    }

def update_poi_gps(poi_id: int, lat: float, lon: float):
    """Dynamically drops WGS84 floats directly resolving missing 999.0 boundaries."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE media_pois SET lat = ?, lon = ? WHERE id = ?', (lat, lon, poi_id))
    conn.commit()
    conn.close()

def update_poi_filepath(poi_id: int, new_filepath: str):
    """Updates physical local OS mapping targeting renamed media files."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE media_pois SET filepath = ? WHERE id = ?', (new_filepath, poi_id))
    conn.commit()
    conn.close()

def insert_measurement(name: str, lat1: float, lon1: float, lat2: float, lon2: float, dist: float, bearing: float, location_id: int = 1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    import datetime
    ts = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO measurements (name, lat1, lon1, lat2, lon2, distance_m, bearing_deg, timestamp, location_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, lat1, lon1, lat2, lon2, dist, bearing, ts, location_id))
    conn.commit()
    conn.close()

def get_all_measurements(location_id: int = 1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id, name, lat1, lon1, lat2, lon2, distance_m, bearing_deg, timestamp FROM measurements WHERE location_id = ?', (location_id,))
        rows = cursor.fetchall()
    except sqlite3.OperationalError: # If table has not yet populated gracefully avoid crashes catching blank mappings
        rows = []
    conn.close()
    return [{'id': r[0], 'name': r[1], 'lat1': r[2], 'lon1': r[3], 'lat2': r[4], 'lon2': r[5], 'distance_m': r[6], 'bearing_deg': r[7], 'timestamp': r[8]} for r in rows]

def delete_measurement(uid: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM measurements WHERE id = ?', (uid,))
    conn.commit()
    conn.close()

def update_measurement_name(uid: int, new_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE measurements SET name = ? WHERE id = ?', (new_name, uid))
    conn.commit()
    conn.close()
