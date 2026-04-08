from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget
import os

from map_engine.builder import generate_base_map

from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtCore import QUrlQuery

class SupaWebPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if url.scheme() == "supabridge":
            query = QUrlQuery(url)
            poi_id = query.queryItemValue("id")
            
            if url.host() == "save_note":
                note = query.queryItemValue("note")
                from core.db_manager import update_note
                try:
                    update_note(int(poi_id), note)
                    print(f"[Bridge] Successfully updated note for POI {poi_id}")
                except Exception as e:
                    print(f"[Bridge] Failed to update note: {e}")
                    
            elif url.host() == "rotate_photo":
                from core.db_manager import get_poi_rotation, update_poi_rotation
                try:
                    current_rot = get_poi_rotation(int(poi_id))
                    new_rot = (current_rot + 90) % 360
                    update_poi_rotation(int(poi_id), new_rot)
                    print(f"[Bridge] Rotated POI {poi_id} to {new_rot} degrees")
                    
                    # Visually inject rotation seamlessly without reloading popup
                    js_rotate = f"document.getElementById('photo_{poi_id}').style.transform = 'rotate({new_rot}deg)';"
                    self.runJavaScript(js_rotate)
                except Exception as e:
                    print(f"[Bridge] Failed to rotate photo: {e}")

            elif url.host() == "play_video":
                from core.db_manager import get_poi
                import os
                try:
                    poi_data = get_poi(int(poi_id))
                    if poi_data and os.path.exists(poi_data['filepath']):
                        os.startfile(os.path.normpath(poi_data['filepath']))
                        print(f"[Bridge] Launched Native Video Player for {poi_id}")
                except Exception as e:
                    print(f"[Bridge] Failed launching video: {e}")

            elif url.host() == "assign_gps":
                target_id = int(query.queryItemValue("id"))
                lat = float(query.queryItemValue("lat"))
                lon = float(query.queryItemValue("lon"))
                from core.db_manager import update_poi_gps
                try:
                    update_poi_gps(target_id, lat, lon)
                    print(f"[Bridge] Re-assigned GPS limits mapping natively to {lat}, {lon}")
                    
                    # Force the whole python engine to visually restart bounds loading newly assigned limits
                    p = self.parent().window()
                    p.refresh_media_list()
                    p.refresh_stats()
                    # Trigger reload mapping cleanly tracking window scopes
                    p.map_view.load_map(os.path.join(p.proj_root, "project_data"), p.current_start, p.current_end)
                except Exception as e:
                    print(f"[Bridge] Failed assigning mapping constraint: {e}")

            elif url.host() == "save_region":
                import os
                import urllib.parse
                import json
                coords_str = urllib.parse.unquote(query.queryItemValue("coords"))
                coords = json.loads(coords_str)
                
                # Natively calculate Acres bounding the Leaflet coordinates!
                from core.geometry import calculate_polygon_metrics
                _, acres, _ = calculate_polygon_metrics(coords)
                
                from core.db_manager import insert_region, get_all_regions
                p = self.parent().window()
                total_regions = len(get_all_regions(p.current_location_id))
                region_name = f"Region {total_regions + 1}"
                
                insert_region(region_name, coords_str, acres, p.current_location_id)
                print(f"[Bridge] Pushed new Geometry Region natively: {acres:.2f} Acres")
                
                # Natively reload Folium binding new table arrays tracking strictly PySide bounds!
                p.refresh_regions_list()
                p.map_view.load_map(os.path.join(p.proj_root, "project_data"), p.current_start, p.current_end, location_id=p.current_location_id)

            elif url.host() == "measure_los":
                import os
                lat1 = float(query.queryItemValue("lat1"))
                lon1 = float(query.queryItemValue("lon1"))
                lat2 = float(query.queryItemValue("lat2"))
                lon2 = float(query.queryItemValue("lon2"))
                
                from core.geometry import calculate_line_of_sight
                from core.db_manager import insert_measurement, get_all_measurements
                
                p = self.parent().window()
                
                bearing, dist_m, dist_ft = calculate_line_of_sight(lat1, lon1, lat2, lon2)
                total_lines = len(get_all_measurements(p.current_location_id))
                line_name = f"Line {total_lines + 1}"
                
                insert_measurement(line_name, lat1, lon1, lat2, lon2, dist_m, bearing, p.current_location_id)
                print(f"[Bridge] Pushed new Geometry measurement binding natively: {dist_m:.2f}m")
                
                # Natively reload Folium binding new table arrays tracking strictly PySide bounds!
                p.refresh_measurements_list()
                p.map_view.load_map(os.path.join(p.proj_root, "project_data"), p.current_start, p.current_end, location_id=p.current_location_id)

            return False # Cancel navigation
        return super().acceptNavigationRequest(url, _type, isMainFrame)

class MapView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view = QWebEngineView()
        
        # Deploy custom bridged page
        self.web_view.setPage(SupaWebPage(self.web_view))
        
        # Enable loading of local files (like our thumbnails)
        settings = self.web_view.page().settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        
        self.layout.addWidget(self.web_view)
    
    def load_map(self, project_data_dir: str, start_date: str = None, end_date: str = None, location_id: int = 1):
        """Loads the Folium HTML map into the QWebEngineView."""
        map_html = generate_base_map(project_data_dir, start_date, end_date, location_id)
        self.web_view.setHtml(map_html)

    def toggle_layer(self, category: str, visible: bool):
        """
        Executes raw JS inside the embedded browser to add/remove Leaflet layer.
        """
        # supaMap and supaLayers are bridged properties via folium payload.
        # Add a tiny delay internally in JS if needed or simply execute instantly.
        js_template = f"""
        if (window.supaMap && window.supaLayers) {{
            var targetLayer = window.supaLayers["{category}"];
            if (targetLayer) {{
                if ({str(visible).lower()}) {{
                    window.supaMap.addLayer(targetLayer);
                }} else {{
                    window.supaMap.removeLayer(targetLayer);
                }}
            }}
        }}
        """
        self.web_view.page().runJavaScript(js_template)

    def add_photo_marker(self, lat: float, lon: float, popup_html: str):
        """Injects a new photo marker onto the map locally without refreshing."""
        safe_html = popup_html.replace('`', '\\`')
        js_cmd = f"""
        if (window.supaMap && window.supaLayers && window.supaLayers['photos']) {{
            var m = L.marker([{lat}, {lon}]);
            m.bindPopup(`{safe_html}`, {{maxWidth: 180}});
            window.supaLayers['photos'].addLayer(m);
        }}
        """
        self.web_view.page().runJavaScript(js_cmd)

    def toggle_measure_tool(self, active: bool):
        is_active = 'true' if active else 'false'
        js = f"""
        if (window.supaMeasureState) {{ 
            window.supaMeasureState.active = {is_active}; 
            window.supaMeasureState.click1 = null; 
            
            if ({is_active}) {{
                window.supaMap.getContainer().style.cursor = 'crosshair';
            }} else {{
                window.supaMap.getContainer().style.cursor = '';
                if (window.supaMeasureState.tempMarker) {{
                    window.supaMap.removeLayer(window.supaMeasureState.tempMarker);
                    window.supaMeasureState.tempMarker = null;
                }}
            }}
        }}
        """
        self.web_view.page().runJavaScript(js)
        
    def toggle_area_tool(self, active: bool):
        is_active = 'true' if active else 'false'
        js = f"""
        if (window.supaAreaState) {{
            window.supaAreaState.active = {is_active};
            if ({is_active}) {{
                window.supaMap.getContainer().style.cursor = 'crosshair';
                window.supaMap.doubleClickZoom.disable();
            }} else {{
                window.supaMap.getContainer().style.cursor = '';
                window.supaMap.doubleClickZoom.enable();
                if (window.supaAreaState.tempPoly) window.supaMap.removeLayer(window.supaAreaState.tempPoly);
                window.supaAreaState.tempMarkers.forEach(mb => window.supaMap.removeLayer(mb));
                window.supaAreaState.points = [];
                window.supaAreaState.tempMarkers = [];
                window.supaAreaState.tempPoly = null;
            }}
        }}
        """
        self.web_view.page().runJavaScript(js)

    def apply_map_style(self, style_name: str):
        css_filter = "none"
        if style_name == "Vibrant (Saturated)":
            css_filter = "saturate(1.5) contrast(1.15) brightness(1.05)"
        elif style_name == "High Contrast":
            css_filter = "contrast(1.6) brightness(0.9)"
        elif style_name == "Darkened":
            css_filter = "brightness(0.65) contrast(1.1)"
        elif style_name == "Black & White":
            css_filter = "grayscale(100%) contrast(1.2)"
            
        js = f"""
            var pane = document.querySelector('.leaflet-tile-pane');
            if(pane) {{
                pane.style.filter = '{css_filter}';
            }}
        """
        self.web_view.page().runJavaScript(js)

    def start_location_assignment(self, poi_id: int):
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Placement Mode Active")
        msg.setText("<span style='color: white; font-size: 14px;'>Click any physical location on the map to anchor this asset.</span>")
        msg.setStyleSheet("QMessageBox { background-color: #0f172a; } QLabel { color: white; } QPushButton { background-color: #3b82f6; color: white; border-radius: 4px; padding: 5px; }")
        msg.exec()
        js = f"""
        if (window.supaLocationState) {{
            window.supaLocationState.active = true;
            window.supaLocationState.targetId = {poi_id};
            window.supaMap.getContainer().style.cursor = 'crosshair';
        }}
        """
        self.web_view.page().runJavaScript(js)
