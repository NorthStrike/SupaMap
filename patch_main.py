import re

with open("ui/main_window.py", "r", encoding="utf-8") as f:
    data = f.read()

data = data.replace(
    '''target_dir = os.path.join(self.proj_root, "project_data", "gpx", category)''',
    '''target_dir = os.path.join(self.proj_root, "project_data", "locations", str(self.current_location_id), "gpx", category)'''
)

data = data.replace(
    '''parsed = load_all_gpx(os.path.join(self.proj_root, "project_data", "gpx"))''',
    '''parsed = load_all_gpx(os.path.join(self.proj_root, "project_data", "locations", str(self.current_location_id), "gpx"))'''
)

data = data.replace(
    '''media = fetch_media_stats(self.current_start, self.current_end)''',
    '''media = fetch_media_stats(self.current_location_id, self.current_start, self.current_end)'''
)

data = data.replace(
    '''pois = get_all_pois(self.current_start, self.current_end)''',
    '''pois = get_all_pois(self.current_location_id, self.current_start, self.current_end)'''
)

data = data.replace(
    '''for m in get_all_measurements():''',
    '''for m in get_all_measurements(self.current_location_id):'''
)

data = re.sub(
    r'\.load_map\(os\.path\.join\([^,]+,\s*"project_data"\),\s*self\.current_start,\s*self\.current_end\)',
    '.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)',
    data
)
data = re.sub(
    r'\.load_map\(os\.path\.join\([^,]+,\s*"project_data"\),\s*p\.current_start,\s*p\.current_end\)',
    '.load_map(os.path.join(p.proj_root, "project_data"), p.current_start, p.current_end, location_id=p.current_location_id)',
    data
)

data = data.replace(
    '''self.current_end = None''',
    '''self.current_end = None\n        self.current_location_id = 1'''
)

data = data.replace(
    '''poi_id = insert_poi(
                poi_type='photo',''',
    '''poi_id = insert_poi(
                location_id=self.current_location_id,
                poi_type='photo','''
)
data = data.replace(
    '''poi_id = insert_poi(
                poi_type='video',''',
    '''poi_id = insert_poi(
                location_id=self.current_location_id,
                poi_type='video','''
)

with open("ui/main_window.py", "w", encoding="utf-8") as f:
    f.write(data)
