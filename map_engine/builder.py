import os
import folium
from folium.plugins import MeasureControl, MousePosition
from jinja2 import Template

def generate_base_map(project_data_dir: str, start_date: str = None, end_date: str = None, location_id: int = 1, center_coords: list = None) -> str:
    """
    Generate the base folium map centered on dynamic location.
    Parses GPX files natively and injects layer controls.
    """
    if center_coords is None:
        from core.db_manager import get_location
        loc = get_location(location_id)
        if loc:
            center_coords = [loc['lat'], loc['lon']]
        else:
            center_coords = [44.82702, -76.51533]
            
    m = folium.Map(
        location=center_coords,
        zoom_start=14,
        control_scale=True,
        tiles=None
    )
    
    # Esri Global Satellite Tracker (Default)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri Satellite bounds',
        name='Satellite imagery',
        max_zoom=20,
        max_native_zoom=17,
        show=True
    ).add_to(m)
    
    # Optional Topographic Engine Module
    folium.TileLayer(
        'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        attr='Map data: &copy; OpenStreetMap contributors | Map style: &copy; OpenTopoMap (CC-BY-SA)',
        name='Topographic Map',
        max_zoom=20,
        max_native_zoom=17,
        show=False
    ).add_to(m)
    
    # Dark Mode Base
    folium.TileLayer(
        tiles="CartoDB dark_matter",
        name='Dark Mode bounds',
        show=False
    ).add_to(m)
    
    # Plugin 1: Live GPS Mouse Position Tracker
    
    # Plugin 2: Live GPS Mouse Position Tracker
    MousePosition(
        position='bottomright',
        separator=' | ',
        empty_string='N/A',
        lng_first=False,
        num_digits=5,
        prefix='GPS:'
    ).add_to(m)
    
    # Inject Dark Mode restyling for the Leaflet Control Plugins bounding the aesthetic
    plugin_styles = """
    <style>
      /* Mouse Position UI */
      .leaflet-container .leaflet-control-mouseposition { background-color: rgba(30,41,59,0.9) !important; color: #3b82f6 !important; padding: 6px 10px !important; border-radius: 4px !important; border: 1px solid #3b82f6 !important; font-family: monospace !important; font-size: 12px !important; font-weight: bold !important; }
    </style>
    """
    m.get_root().header.add_child(folium.Element(plugin_styles))
    
    # 1. Fetch Data targeting specific workspace locations!
    from core.gpx_parser import load_all_gpx
    gpx_dir = os.path.join(project_data_dir, "locations", str(location_id), "gpx")
    data = load_all_gpx(gpx_dir)
    
    # 2. Build FeatureGroups for Categories
    styles = {
        'trails': {'color': 'green', 'weight': 3, 'fill': False, 'dashArray': None},
        'ponds': {'color': 'blue', 'weight': 2, 'fill': True, 'fillOpacity': 0.5},
        'cliffs': {'color': '#8B4513', 'weight': 3, 'fill': False, 'dashArray': None}, # Brown
        'boundaries': {'color': 'red', 'weight': 4, 'fill': False, 'dashArray': '10, 10'}
    }
    
    js_layer_map = []
    
    for category, lines in data.items():
        fg = folium.FeatureGroup(name=category.capitalize(), control=False)
        style = styles.get(category, {})
        
        for item in lines:
            coords = item['coords']
            path_coords = [(c[0], c[1]) for c in coords]
            min_e = item.get('min_ele')
            max_e = item.get('max_ele')
            dist = item.get('distance_2d', 0)
            
            if category == 'trails' and min_e is not None:
                import branca.colormap as cm
                import matplotlib.pyplot as plt
                import io
                import base64
                
                elevations = [c[2] if c[2] is not None else min_e for c in coords]
                colormap = cm.LinearColormap(colors=['green', 'yellow', 'red'], vmin=min_e, vmax=max_e)
                
                avg_gr = item.get('avg_grade', 0)
                max_gr = item.get('max_grade', 0)
                
                # Headless Matplotlib Graph
                fig, ax = plt.subplots(figsize=(4, 2.2))
                ax.plot(elevations, color='#ef4444', linewidth=2)
                ax.fill_between(range(len(elevations)), elevations, min(elevations)-5, color='#ef4444', alpha=0.3)
                ax.set_title(f"Distance: {dist:.1f}m | Elev: {min_e:.0f}m - {max_e:.0f}m\nGrade: {avg_gr:.1f}% Avg | {max_gr:.1f}% Max", fontsize=9, color='white')
                ax.set_facecolor('#1e293b')
                fig.patch.set_facecolor('#0f172a')
                ax.tick_params(colors='white', labelsize=7)
                for spine in ax.spines.values():
                    spine.set_color('#334155')
                fig.tight_layout()
                
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=100)
                plt.close(fig)
                b64_chart = base64.b64encode(buf.getvalue()).decode('utf-8')
                
                popup_html = f"<div style='background:#0f172a; padding:5px; border-radius:4px;'><img src='data:image/png;base64,{b64_chart}' style='border-radius:4px;'></div>"
                
                folium.ColorLine(
                    positions=path_coords,
                    colors=elevations,
                    colormap=colormap,
                    weight=4
                ).add_child(folium.Popup(popup_html, max_width=450)).add_to(fg)
                
            elif (item.get('is_polygon') and category != 'boundaries') or style.get('fill', False):
                filename = item.get('name', 'Unknown')
                
                if 'pond' in filename or 'water' in filename or category == 'ponds':
                    poly_color = '#3b82f6'
                    poly_fill = '#60a5fa'
                    p_type = 'Water Body'
                elif 'clearing' in filename or 'stand' in filename:
                    poly_color = '#65a30d'
                    poly_fill = '#a3e635'
                    p_type = 'Land / Clearing'
                else:
                    poly_color = style.get('color', '#ffffff')
                    poly_fill = style.get('color', '#ffffff')
                    p_type = category.capitalize()
                    
                area_acres = item.get('area_acres', 0)
                area_sqm = item.get('area_sqm', 0)
                perim = item.get('perimeter_m', 0)
                
                popup_html = f"<div style='background:#1e293b; padding:10px; border-radius:4px; color:#f8fafc; font-family:sans-serif;'><h4 style='margin:0 0 5px 0; color:{poly_fill}; border-bottom:1px solid #334155; padding-bottom:3px;'>{p_type}</h4><div style='font-size:12px;'><strong>Area:</strong> {area_acres:.2f} acres<br><span style='color:#94a3b8;'>({area_sqm:.0f} sq meters)</span><br><br><strong>Perimeter:</strong> {perim:.0f} meters</div></div>"
                
                folium.Polygon(
                    locations=path_coords,
                    color=poly_color,
                    weight=style.get('weight', 3),
                    fill=True,
                    fill_opacity=style.get('fillOpacity', 0.4),
                    fill_color=poly_fill
                ).add_child(folium.Popup(popup_html, max_width=300)).add_to(fg)
            else:
                folium.PolyLine(
                    locations=path_coords,
                    color=style['color'],
                    weight=style['weight'],
                    dash_array=style.get('dashArray')
                ).add_to(fg)
                
            # If these are boundaries, calculate the bounding box for fit_bounds
            if category == 'boundaries' and coords:
                lats = [c[0] for c in coords]
                lons = [c[1] for c in coords]
                min_lat, max_lat = min(lats), max(lats)
                min_lon, max_lon = min(lons), max(lons)
                
                # Shrink bounding box by 5% to force Leaflet's fitBounds to zoom in tightly without clipping corners!
                lat_margin = (max_lat - min_lat) * 0.05
                lon_margin = (max_lon - min_lon) * 0.05
                
                m.fit_bounds([
                    [min_lat + lat_margin, min_lon + lon_margin], 
                    [max_lat - lat_margin, max_lon - lon_margin]
                ])
        
        fg.add_to(m)
        
        # Track the dynamic JS variable name representing this FeatureGroup
        # fg.get_name() outputs something like 'feature_group_...' which is the variable name inside the HTML script
        js_layer_map.append(f"'{category}': {fg.get_name()}")
    
    # 2.5 Fetch and inject Database Media POIs
    from core.db_manager import get_all_pois
    import base64
    
    def get_b64(filepath):
        if not os.path.exists(filepath): return ""
        with open(filepath, "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")
            
    pois = get_all_pois(location_id=location_id, start_date=start_date, end_date=end_date)
    fg_photos = folium.FeatureGroup(name="Photos", control=False)
    fg_videos = folium.FeatureGroup(name="Videos", control=False)
    fg_cones = folium.FeatureGroup(name="Photo Cones", control=False)
    
    for p in pois:
        if p['lat'] == 999.0:
            continue
            
        poi_id = p.get('id')
        filename = os.path.splitext(os.path.basename(p['filepath']))[0]
        timestamp = p.get('timestamp') or 'Unknown Time'
        heading_str = f"Heading: {p['heading']:.1f}&deg;" if p.get('heading') else "Heading: N/A"
        notes = p.get('notes') or ""
        
        if p['type'] == 'photo':
            thumb_path = p['filepath']
            b64_img = get_b64(thumb_path)
            rotation = p.get('rotation', 0)
            
            popup_html = f"""
            <div style="font-family: sans-serif; text-align: center; width: 150px;">
                <div style="width: 150px; height: 150px; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px auto;">
                    <img id="photo_{poi_id}" src='{b64_img}' style="max-width: 150px; max-height: 150px; border-radius: 4px; transform: rotate({rotation}deg); transition: transform 0.2s ease-in-out;">
                </div>
                <div style="font-size: 11px;"><b>{filename}</b></div>
                <div style="font-size: 10px; color: gray;">{timestamp[:16]}</div>
                <div style="font-size: 10px; margin-bottom: 5px;">{heading_str}</div>
                <hr style="margin:4px 0;">
                <textarea id="note_{poi_id}" placeholder="Type note here..." style="width: 140px; height: 50px; font-size: 11px; resize: none;">{notes}</textarea><br>
                <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                    <button style="font-size:10px; cursor:pointer; flex: 1; margin-right: 2px;" onclick="window.location.href='supabridge://save_note?id={poi_id}&note=' + encodeURIComponent(document.getElementById('note_{poi_id}').value)">Save Note</button>
                    <button style="font-size:10px; cursor:pointer; flex: 1; margin-left: 2px;" onclick="window.location.href='supabridge://rotate_photo?id={poi_id}'">Rotate ↻</button>
                </div>
            </div>
            """
            
            folium.Marker(
                location=[p['lat'], p['lon']],
                popup=folium.Popup(popup_html, max_width=200)
            ).add_to(fg_photos)
            
            if p.get('heading') is not None:
                from folium.plugins import SemiCircle
                SemiCircle(
                    location=[p['lat'], p['lon']],
                    radius=50,
                    direction=p['heading'],
                    arc=60,
                    color='yellow',
                    fill_color='yellow',
                    fill_opacity=0.4,
                    weight=1
                ).add_to(fg_cones)

        elif p['type'] == 'video':
            # Create supalocal path
            abs_vid = os.path.abspath(p['filepath']).replace("\\", "/")
            if not abs_vid.startswith("/"):
                abs_vid = "/" + abs_vid

            # Load thumbnail if available extracted by OpenCV natively!
            filename_with_ext = os.path.basename(p['filepath'])
            thumb_path = os.path.join(project_data_dir, "thumbnails", filename_with_ext + ".jpg")
            
            # Retroactively generate missing thumbnails for videos uploaded before native OpenCV integration
            if not os.path.exists(thumb_path):
                try:
                    import cv2
                    vidcap = cv2.VideoCapture(p['filepath'])
                    success, image = vidcap.read()
                    if success:
                        h, w = image.shape[:2]
                        min_dim = min(h, w)
                        sy, sx = (h - min_dim) // 2, (w - min_dim) // 2
                        cropped = image[sy:sy+min_dim, sx:sx+min_dim]
                        img_resized = cv2.resize(cropped, (150, 150), interpolation=cv2.INTER_AREA)
                        cv2.imwrite(thumb_path, img_resized)
                    vidcap.release()
                except Exception:
                    pass
                    
            b64_img = get_b64(thumb_path)
            
            if b64_img:
                vid_box_style = f"width: 150px; height: 150px; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px auto; cursor: pointer; background: url('{b64_img}') center/cover; border-radius: 4px; border: 1px solid #334155; transition: 0.2s;"
                vid_inner = '<div style="background: rgba(15, 23, 42, 0.7); width: 40px; height: 40px; border-radius: 20px; display: flex; align-items: center; justify-content: center;"><span style="font-size: 24px; color: #10b981;">▶</span></div>'
            else:
                vid_box_style = "width: 150px; height: 100px; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px auto; cursor: pointer; background: #0f172a; border-radius: 4px; border: 1px solid #334155; transition: 0.2s;"
                vid_inner = '<span style="font-size: 24px; color: #3b82f6;">▶</span><br><span style="color: #94a3b8; font-size: 10px; margin-left: 5px;">Play Video</span>'

            popup_html = f"""
            <div style="font-family: sans-serif; text-align: center; width: 150px;">
                <div style="{vid_box_style}" onclick="window.location.href='supabridge://play_video?id={poi_id}'">
                    {vid_inner}
                </div>
                <div style="font-size: 11px;"><b>{filename}</b></div>
                <div style="font-size: 10px; color: gray;">{timestamp[:16]}</div>
                <div style="font-size: 10px; margin-bottom: 5px;">{heading_str}</div>
                <hr style="margin:4px 0;">
                <textarea id="note_{poi_id}" placeholder="Type note here..." style="width: 140px; height: 50px; font-size: 11px; resize: none;">{notes}</textarea><br>
                <div style="display: flex; justify-content: center; margin-top: 5px;">
                    <button style="font-size:10px; cursor:pointer;" onclick="window.location.href='supabridge://save_note?id={poi_id}&note=' + encodeURIComponent(document.getElementById('note_{poi_id}').value)">Save Note</button>
                </div>
            </div>
            """

            folium.Marker(
                location=[p['lat'], p['lon']],
                popup=folium.Popup(popup_html, max_width=200)
            ).add_to(fg_videos)

    fg_photos.add_to(m)
    fg_videos.add_to(m)
    fg_cones.add_to(m)
    
    # Render Saved Measurements
    from core.db_manager import get_all_measurements
    fg_measure = folium.FeatureGroup(name="Measurements", control=False)
    for msr in get_all_measurements(location_id=location_id):
        coords = [(msr['lat1'], msr['lon1']), (msr['lat2'], msr['lon2'])]
        ttip = f"{msr['name']} | Dist: {msr['distance_m']:.1f}m | Bearing: {msr['bearing_deg']:.1f}&deg;"
        folium.PolyLine(
            locations=coords,
            color='#00ff88',
            weight=4,
            dash_array='6, 8',
            tooltip=ttip
        ).add_to(fg_measure)
    fg_measure.add_to(m)
    
    js_layer_map.append(f"'photos': {fg_photos.get_name()}")
    js_layer_map.append(f"'videos': {fg_videos.get_name()}")
    js_layer_map.append(f"'measurements': {fg_measure.get_name()}")
    
    # Render Saved Regions
    from core.db_manager import get_all_regions
    fg_regions = folium.FeatureGroup(name="Regions (Polygons)", control=False)
    for reg in get_all_regions(location_id=location_id):
        coords = reg['coords']
        ttip = f"<b>{reg['name']}</b><br>Acres: {reg['acres']:.2f}"
        
        folium.Polygon(
            locations=coords,
            color='#3b82f6',
            fill_color='#3b82f6',
            fill_opacity=0.4,
            weight=3,
            tooltip=ttip
        ).add_to(fg_regions)
    fg_regions.add_to(m)
    js_layer_map.append(f"'regions': {fg_regions.get_name()}")
    
    js_layer_map.append(f"'cones': {fg_cones.get_name()}")
    
    # 3. Inject Global Bridge JS payload
    # Expose the layers and map explicitly for Qt WebEngine
    js_layer_dict_str = ", ".join(js_layer_map)
    bridge_script = f"""
    <script>
      window.supaMeasureState = {{
        active: false,
        click1: null
      }};
      
      window.supaAreaState = {{
        active: false,
        points: [],
        tempPoly: null,
        tempMarkers: []
      }};
      
      window.supaLocationState = {{
        active: false,
        targetId: null
      }};

      // Make map and layers accessible globally once constructed
      window.onload = function() {{
        setTimeout(function() {{
            window.supaMap = {m.get_name()};
            window.supaLayers = {{{js_layer_dict_str}}};
            
            // Inject Measurement Interceptor natively avoiding external overrides
            window.supaMap.on('click', function(e) {{
                if (window.supaLocationState.active) {{
                    var url = `supabridge://assign_gps?id=${{window.supaLocationState.targetId}}&lat=${{e.latlng.lat}}&lon=${{e.latlng.lng}}`;
                    window.location.href = url;
                    window.supaLocationState.active = false;
                    window.supaLocationState.targetId = null;
                    return;
                }}
                
                if (window.supaAreaState.active) {{
                    var isFirst = (window.supaAreaState.points.length === 0);
                    window.supaAreaState.points.push([e.latlng.lat, e.latlng.lng]);
                    
                    var marker = L.circleMarker(e.latlng, {{color: isFirst ? '#10b981' : '#3b82f6', radius: isFirst ? 14 : 5, fillOpacity: 1}}).addTo(window.supaMap);
                    window.supaAreaState.tempMarkers.push(marker);
                    
                    if (isFirst) {{
                        marker.bindTooltip("Click to Finish", {{permanent: true, direction: "right", className: "region-finish-tip"}}).openTooltip();
                        marker.on('click', function(ev) {{
                            L.DomEvent.stopPropagation(ev);
                            if (window.supaAreaState.points.length >= 3) {{
                                window.supaMap.fire('dblclick');
                            }} else {{
                                alert("A Region must have at least 3 points!");
                            }}
                        }});
                    }}
                    
                    if (window.supaAreaState.points.length >= 2) {{
                        if (window.supaAreaState.tempPoly) {{
                            window.supaMap.removeLayer(window.supaAreaState.tempPoly);
                        }}
                        window.supaAreaState.tempPoly = L.polygon(window.supaAreaState.points, {{color: '#3b82f6', fillOpacity: 0.4, weight: 3}}).addTo(window.supaMap);
                    }}
                    return;
                }}
            
                if (!window.supaMeasureState.active) return;
                
                if (!window.supaMeasureState.click1) {{
                    window.supaMeasureState.click1 = e.latlng;
                    window.supaMeasureState.tempMarker = L.circleMarker(e.latlng, {{color: '#00ff88', radius: 6}}).addTo(window.supaMap);
                }} else {{
                    var click2 = e.latlng;
                    var url = `supabridge://measure_los?lat1=${{window.supaMeasureState.click1.lat}}&lon1=${{window.supaMeasureState.click1.lng}}&lat2=${{click2.lat}}&lon2=${{click2.lng}}`;
                    window.location.href = url;
                    
                    if (window.supaMeasureState.tempMarker) {{
                        window.supaMap.removeLayer(window.supaMeasureState.tempMarker);
                        window.supaMeasureState.tempMarker = null;
                    }}
                    window.supaMeasureState.click1 = null; 
                }}
            }});
            
            window.supaMap.on('dblclick', function(e) {{
                if (window.supaAreaState.active && window.supaAreaState.points.length >= 3) {{
                    var coordsStr = JSON.stringify(window.supaAreaState.points);
                    var url = `supabridge://save_region?coords=${{encodeURIComponent(coordsStr)}}`;
                    window.location.href = url;
                    
                    window.supaAreaState.active = false;
                    if (window.supaAreaState.tempPoly) window.supaMap.removeLayer(window.supaAreaState.tempPoly);
                    window.supaAreaState.tempMarkers.forEach(mb => window.supaMap.removeLayer(mb));
                    window.supaAreaState.points = [];
                    window.supaAreaState.tempMarkers = [];
                    window.supaAreaState.tempPoly = null;
                    window.supaMap.getContainer().style.cursor = '';
                    window.supaMap.doubleClickZoom.enable();
                }} else if (window.supaAreaState.active) {{
                    alert("A Region must have at least 3 points!");
                }}
            }});
            
            console.log("Bridged SupaLayers setup cleanly.");
        }}, 500); // Give Leaflet half a sec to bind fully
      }};
    </script>
    """
    
    # Integrate layer toggling mechanism for TopoMap
    folium.LayerControl().add_to(m)
    m.get_root().html.add_child(folium.Element(bridge_script))
    
    return m.get_root().render()
