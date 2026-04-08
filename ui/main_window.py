from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QPushButton, QCheckBox, QFileDialog, QMessageBox, QComboBox
)
from PySide6.QtCore import Qt
import os
import datetime

from ui.map_view import MapView
from core.media_handler import process_and_save_upload, process_and_save_video_upload
from core.db_manager import insert_poi

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("SupaMap - Maberly Explorer")
        self.resize(1400, 900)
        
        # Central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        from core.system_paths import get_install_dir, get_bundle_dir
        self.proj_root = get_install_dir()
        self.bundle_root = get_bundle_dir()
        
        # Build Map Area First (so sidebar can hook into it)
        self.setup_map_area()
        self.setup_sidebar()
        
        self.load_stylesheet()
        
        # Load the map dynamically using actual paths
        self.map_view.load_map(os.path.join(self.proj_root, "project_data"))

    def setup_map_area(self):
        # Map Area using Folium QtWebEngine integration
        self.map_view = MapView()
        self.main_layout.addWidget(self.map_view)

    def setup_sidebar(self):
        from PySide6.QtWidgets import QScrollArea
        
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setFixedWidth(330)
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFrameShape(QFrame.NoFrame)
        self.sidebar_scroll.setStyleSheet("QScrollArea { border: none; background: #0f172a; } QScrollBar:vertical { width: 10px; }")

        # Sidebar Frame
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar_scroll.setWidget(self.sidebar)
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setAlignment(Qt.AlignTop)
        
        # Title Label
        title = QLabel("SupaMap")
        title.setProperty("role", "title")
        
        self.sidebar_layout.addWidget(title)
        
        # Dashboard Panel / Stats 
        stats_header = QLabel("Property Stats")
        stats_header.setProperty("role", "header")
        self.sidebar_layout.addWidget(stats_header)
        
        self.lbl_prop_area = QLabel("Property Limit: -- acres")
        self.lbl_trail_dist = QLabel("Total Trails: -- km")
        self.lbl_ponds = QLabel("Ponds: -- (-- acres)")
        self.lbl_cliffs = QLabel("Cliffs: -- (-- km)")
        self.lbl_media_count = QLabel("Media: --")
        
        # Styling dashboard labels
        for lbl in [self.lbl_prop_area, self.lbl_trail_dist, self.lbl_ponds, self.lbl_cliffs, self.lbl_media_count]:
            lbl.setStyleSheet("font-size: 11px; color:#cbd5e1; padding: 2px;")
            self.sidebar_layout.addWidget(lbl)
            
        self.sidebar_layout.addSpacing(10)
        
        # Interactive Tools (Moved)
        tools_header = QLabel("Interactive Tools")
        tools_header.setProperty("role", "header")
        self.sidebar_layout.addWidget(tools_header)
        
        # Mapping Visual Enhancers
        self.map_style_combo = QComboBox()
        self.map_style_combo.addItems(["Natural View", "Vibrant (Saturated)", "High Contrast", "Darkened", "Black & White"])
        self.map_style_combo.setStyleSheet("background-color: #1e293b; color: white; padding: 4px; border: 1px solid #334155; border-radius: 4px; margin-bottom: 5px;")
        self.map_style_combo.wheelEvent = lambda event: event.ignore()  # Prevent scroll stealing
        self.map_style_combo.currentTextChanged.connect(self.map_view.apply_map_style)
        self.sidebar_layout.addWidget(self.map_style_combo)
        
        self.sidebar_layout.addSpacing(10)
        
        # Layers Header
        layer_header = QLabel("Map Features")
        layer_header.setProperty("role", "header")
        self.sidebar_layout.addWidget(layer_header)
        
        categories = ["trails", "ponds", "cliffs", "boundaries", "photos", "videos", "cones"]
        self.layer_checkboxes = {}
        
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(5)
        
        row, col = 0, 0
        for cat in categories:
            cb = QCheckBox(cat.capitalize())
            cb.setChecked(True) # Started as true since they render initially
            
            # Using partial equivalence with closure capture
            cb.stateChanged.connect(self._create_toggle_lambda(cat, cb))
            
            grid.addWidget(cb, row, col)
            self.layer_checkboxes[cat] = cb
            
            col += 1
            if col > 1:
                col = 0
                row += 1
                
        self.sidebar_layout.addLayout(grid)
        self.sidebar_layout.addSpacing(10)
        
        # Temporal Filter
        temp_header = QLabel("Time Filter")
        temp_header.setProperty("role", "header")
        self.sidebar_layout.addWidget(temp_header)
        
        self.current_start = None
        self.current_end = None
        self.current_location_id = 1
        
        filter_layout = QHBoxLayout()
        self.season_box = QComboBox()
        self.season_box.addItems(["Any Season", "Spring", "Summer", "Fall", "Winter"])
        self.season_box.wheelEvent = lambda event: event.ignore()  # Prevent scroll stealing
        self.season_box.currentTextChanged.connect(self.on_filter_changed)
        
        self.year_box = QComboBox()
        self.year_box.addItems(["Any Year", "2023", "2024", "2025", "2026"])
        self.year_box.wheelEvent = lambda event: event.ignore()  # Prevent scroll stealing
        self.year_box.currentTextChanged.connect(self.on_filter_changed)
        
        filter_layout.addWidget(self.season_box)
        filter_layout.addWidget(self.year_box)
        self.sidebar_layout.addLayout(filter_layout)
        
        self.sidebar_layout.addSpacing(10)
        

        # Property Geometry Tree
        from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
        self.geometry_tree = QTreeWidget()
        self.geometry_tree.setHeaderHidden(True)
        self.geometry_tree.setObjectName("GeometryTree")
        self.geometry_tree.setMinimumHeight(150)
        self.geometry_tree.setStyleSheet("QTreeWidget { background-color: #1e293b; color: white; border: 1px solid #334155; border-radius: 4px; padding: 4px; font-size: 11px; } QTreeWidget::item:hover { background-color: #334155; }")
        self.sidebar_layout.addWidget(self.geometry_tree)
            
        geom_up_layout = QHBoxLayout()
        geom_up_layout.setSpacing(4)
        
        btn_up_trail = QPushButton("+ Trail")
        btn_up_trail.setObjectName("BtnGreen")
        btn_up_trail.setStyleSheet("color: white; font-weight: bold; padding: 3px; font-size: 11px;")
        btn_up_trail.clicked.connect(lambda: self.upload_specific_gpx("trails"))
        
        btn_up_pond = QPushButton("+ Pond")
        btn_up_pond.setObjectName("BtnBlue")
        btn_up_pond.setStyleSheet("color: white; font-weight: bold; padding: 3px; font-size: 11px;")
        btn_up_pond.clicked.connect(lambda: self.upload_specific_gpx("ponds"))
        
        btn_up_cliff = QPushButton("+ Cliff")
        btn_up_cliff.setObjectName("BtnYellow")
        btn_up_cliff.setStyleSheet("color: black; font-weight: bold; padding: 3px; font-size: 11px;")
        btn_up_cliff.clicked.connect(lambda: self.upload_specific_gpx("cliffs"))
        
        geom_up_layout.addWidget(btn_up_trail)
        geom_up_layout.addWidget(btn_up_pond)
        geom_up_layout.addWidget(btn_up_cliff)
        self.sidebar_layout.addLayout(geom_up_layout)
            
        geom_btn_layout = QHBoxLayout()
        geom_btn_layout.setSpacing(4)
        
        btn_rename_geom = QPushButton("Rename Selected")
        btn_rename_geom.setObjectName("BtnBlue")
        btn_rename_geom.setStyleSheet("padding: 3px; font-size: 11px;")
        btn_rename_geom.clicked.connect(self.rename_selected_geometry)
        
        btn_delete_geom = QPushButton("Delete Selected")
        btn_delete_geom.setObjectName("BtnRed")
        btn_delete_geom.setStyleSheet("padding: 3px; font-size: 11px;")
        btn_delete_geom.clicked.connect(self.delete_selected_geometry)
        
        geom_btn_layout.addWidget(btn_rename_geom)
        geom_btn_layout.addWidget(btn_delete_geom)
        self.sidebar_layout.addLayout(geom_btn_layout)
        
        self.sidebar_layout.addSpacing(20)


        

        # Media / External
        media_header = QLabel("Add Assets")
        media_header.setProperty("role", "header")
        self.sidebar_layout.addWidget(media_header)
        
        upload_btn = QPushButton("Upload Photo")
        upload_btn.setObjectName("BtnBlue")
        upload_btn.setStyleSheet("padding: 3px; font-size: 11px;")
        upload_btn.clicked.connect(self.upload_photo)
        self.sidebar_layout.addWidget(upload_btn)
        
        upload_vid_btn = QPushButton("Upload Video")
        upload_vid_btn.setObjectName("BtnBlue")
        upload_vid_btn.setStyleSheet("padding: 3px; font-size: 11px;")
        upload_vid_btn.clicked.connect(self.upload_video)
        self.sidebar_layout.addWidget(upload_vid_btn)
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        
        # Photos List
        photo_lbl = QLabel("Photos:")
        photo_lbl.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.sidebar_layout.addWidget(photo_lbl)
        self.photo_list = QListWidget()
        self.photo_list.setObjectName("PhotoList")
        self.photo_list.setMinimumHeight(100)
        self.sidebar_layout.addWidget(self.photo_list)
        
        # Videos List
        video_lbl = QLabel("Videos:")
        video_lbl.setStyleSheet("color: #94a3b8; font-weight: bold;")
        self.sidebar_layout.addWidget(video_lbl)
        self.video_list = QListWidget()
        self.video_list.setObjectName("VideoList")
        self.video_list.setMinimumHeight(80)
        self.sidebar_layout.addWidget(self.video_list)
        

        media_btn_layout = QHBoxLayout()
        media_btn_layout.setSpacing(4)
        
        self.rename_btn = QPushButton("Rename")
        self.rename_btn.setObjectName("BtnBlue")
        self.rename_btn.setStyleSheet("padding: 3px; font-size: 11px;")
        self.rename_btn.clicked.connect(self.rename_selected_media)
        
        self.assign_btn = QPushButton("Add GPS")
        self.assign_btn.setObjectName("BtnYellow")
        self.assign_btn.setStyleSheet("color: black; font-weight: bold; padding: 3px; font-size: 11px;")
        self.assign_btn.clicked.connect(self.assign_selected_media)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("BtnRed")
        delete_btn.setStyleSheet("padding: 3px; font-size: 11px;")
        delete_btn.clicked.connect(self.delete_selected_media)
        
        media_btn_layout.addWidget(self.rename_btn)
        media_btn_layout.addWidget(self.assign_btn)
        media_btn_layout.addWidget(delete_btn)
        
        self.sidebar_layout.addLayout(media_btn_layout)
        
        self.sidebar_layout.addSpacing(20)

        # Measurements Section (Moved)
        measure_header = QLabel("Measurements")
        measure_header.setProperty("role", "header")
        self.sidebar_layout.addWidget(measure_header)
        
        self.btn_measure = QPushButton("Measurement Tool (Draw Lines)")
        self.btn_measure.setObjectName("BtnDark")
        self.btn_measure.setStyleSheet("padding: 3px; font-size: 11px;")
        self.btn_measure.setCheckable(True)
        self.btn_measure.toggled.connect(self.map_view.toggle_measure_tool)
        self.sidebar_layout.addWidget(self.btn_measure)
        
        self.btn_area = QPushButton("Region Tool (Draw Polygon Areas)")
        self.btn_area.setObjectName("BtnBlue")
        self.btn_area.setStyleSheet("padding: 3px; font-size: 11px;")
        self.btn_area.setCheckable(True)
        self.btn_area.toggled.connect(self.map_view.toggle_area_tool)
        self.sidebar_layout.addWidget(self.btn_area)
        
        self.measure_list = QListWidget()
        self.measure_list.setObjectName("MeasureList")
        self.measure_list.setMinimumHeight(60)
        self.sidebar_layout.addWidget(self.measure_list)
        
        btn_delete_measure = QPushButton("Delete Selected Line")
        btn_delete_measure.setObjectName("BtnRed")
        btn_delete_measure.setStyleSheet("padding: 3px; font-size: 11px;")
        btn_delete_measure.clicked.connect(self.delete_selected_measurement)
        self.sidebar_layout.addWidget(btn_delete_measure)
        
        self.region_list = QListWidget()
        self.region_list.setObjectName("RegionList")
        self.region_list.setMinimumHeight(60)
        self.sidebar_layout.addWidget(self.region_list)
        
        btn_delete_region = QPushButton("Delete Selected Region")
        btn_delete_region.setObjectName("BtnRed")
        btn_delete_region.setStyleSheet("padding: 3px; font-size: 11px;")
        btn_delete_region.clicked.connect(self.delete_selected_region)
        self.sidebar_layout.addWidget(btn_delete_region)
        
        # Prevent cross-selection collision bugs now that all 5 lists physically exist in memory
        self.photo_list.itemClicked.connect(lambda: (self.video_list.clearSelection(), self.measure_list.clearSelection(), self.geometry_tree.clearSelection(), self.region_list.clearSelection()))
        self.video_list.itemClicked.connect(lambda: (self.photo_list.clearSelection(), self.measure_list.clearSelection(), self.geometry_tree.clearSelection(), self.region_list.clearSelection()))
        self.measure_list.itemClicked.connect(lambda: (self.photo_list.clearSelection(), self.video_list.clearSelection(), self.geometry_tree.clearSelection(), self.region_list.clearSelection()))
        self.geometry_tree.itemClicked.connect(lambda: (self.photo_list.clearSelection(), self.video_list.clearSelection(), self.measure_list.clearSelection(), self.region_list.clearSelection()))
        self.region_list.itemClicked.connect(lambda: (self.photo_list.clearSelection(), self.video_list.clearSelection(), self.measure_list.clearSelection(), self.geometry_tree.clearSelection()))
        
        
        # Data Export tools
        export_header = QLabel("Export Data")
        export_header.setProperty("role", "header")
        export_header.setStyleSheet("color: white; font-weight: bold; font-size: 14px; margin-top: 15px; margin-bottom: 5px;")
        self.sidebar_layout.addWidget(export_header)
        
        self.btn_export_csv = QPushButton("Export Media (CSV)")
        self.btn_export_csv.setObjectName("BtnDark")
        self.btn_export_csv.setStyleSheet("padding: 3px; font-size: 11px;")
        self.btn_export_csv.clicked.connect(self.export_csv_data)
        self.sidebar_layout.addWidget(self.btn_export_csv)
        
        self.btn_export_kml = QPushButton("Export System Map (KML)")
        self.btn_export_kml.setObjectName("BtnDark")
        self.btn_export_kml.setStyleSheet("padding: 3px; font-size: 11px;")
        self.btn_export_kml.clicked.connect(self.export_kml_data)
        self.sidebar_layout.addWidget(self.btn_export_kml)
        
        self.btn_export_pdf = QPushButton("Export Property Map (PDF)")
        self.btn_export_pdf.setObjectName("BtnGreen")
        self.btn_export_pdf.setStyleSheet("color: white; font-weight: bold; padding: 3px; font-size: 11px;")
        self.btn_export_pdf.clicked.connect(self.export_pdf_map)
        self.sidebar_layout.addWidget(self.btn_export_pdf)
        
        self.sidebar_layout.addSpacing(10)
        loc_header = QLabel("Map Location")
        loc_header.setProperty("role", "header")
        self.sidebar_layout.addWidget(loc_header)
        
        loc_layout = QHBoxLayout()
        self.loc_dropdown = QComboBox()
        self.loc_dropdown.setStyleSheet("background-color: #1e293b; color: white; padding: 4px; border: 1px solid #334155; border-radius: 4px;")
        self.loc_dropdown.wheelEvent = lambda event: event.ignore()
        
        loc_layout.addWidget(self.loc_dropdown)
        
        btn_add_loc = QPushButton("+")
        btn_add_loc.setObjectName("BtnGreen")
        btn_add_loc.setStyleSheet("padding: 3px; font-weight: bold; font-size: 14px; max-width: 30px;")
        btn_add_loc.clicked.connect(self.prompt_new_location)
        loc_layout.addWidget(btn_add_loc)
        
        btn_del_loc = QPushButton("-")
        btn_del_loc.setObjectName("BtnRed")
        btn_del_loc.setStyleSheet("padding: 3px; font-weight: bold; font-size: 14px; max-width: 30px;")
        btn_del_loc.clicked.connect(self.prompt_delete_location)
        loc_layout.addWidget(btn_del_loc)
        
        self.sidebar_layout.addLayout(loc_layout)
        self.loc_dropdown.currentIndexChanged.connect(self.on_location_changed)
        
        self.refresh_locations_dropdown()
        self.sidebar_layout.addStretch()
        
        self.refresh_media_list()
        self.refresh_stats()
        
        # Insert sidebar scroll area to the Left
        self.main_layout.insertWidget(0, self.sidebar_scroll)

    def on_filter_changed(self, text=None):
        season = self.season_box.currentText()
        year = self.year_box.currentText()
        
        if year == "Any Year" or season == "Any Season":
            self.current_start = None
            self.current_end = None
        else:
            if season == "Spring":
                self.current_start, self.current_end = f"{year}-03-20T00:00:00", f"{year}-06-20T23:59:59"
            elif season == "Summer":
                self.current_start, self.current_end = f"{year}-06-21T00:00:00", f"{year}-09-21T23:59:59"
            elif season == "Fall":
                self.current_start, self.current_end = f"{year}-09-22T00:00:00", f"{year}-12-20T23:59:59"
            elif season == "Winter":
                self.current_start, self.current_end = f"{year}-12-21T00:00:00", f"{int(year)+1}-03-19T23:59:59"
            
        self.refresh_stats()
        self.refresh_media_list()
        self.map_view.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)
        self.btn_measure.setChecked(False)

    def refresh_stats(self):
        from core.gpx_parser import load_all_gpx
        from core.db_manager import fetch_media_stats
        
        parsed = load_all_gpx(os.path.join(self.proj_root, "project_data", "locations", str(self.current_location_id), "gpx"))
        
        total_boundary = sum(item.get('area_acres', 0) for item in parsed.get('boundaries', []))
        total_trails = sum(item.get('distance_2d', 0) for item in parsed.get('trails', [])) / 1000.0 # KM
        
        pond_items = parsed.get('ponds', [])
        pond_count = len(pond_items)
        pond_acres = sum(item.get('area_acres', 0) for item in pond_items if item.get('is_polygon'))
        
        cliff_items = parsed.get('cliffs', [])
        cliff_count = len(cliff_items)
        cliff_dist = sum(item.get('distance_2d', 0) for item in cliff_items) / 1000.0
        
        media = fetch_media_stats(self.current_location_id, self.current_start, self.current_end)
        
        self.lbl_prop_area.setText(f"Property Base: {total_boundary:.1f} acres")
        self.lbl_trail_dist.setText(f"Total Trails: {total_trails:.2f} km")
        self.lbl_ponds.setText(f"Ponds: {pond_count} ({pond_acres:.2f} acres)")
        self.lbl_cliffs.setText(f"Cliffs: {cliff_count} ({cliff_dist:.2f} km)")
        self.lbl_media_count.setText(f"Media ({media['photos']} Photos | {media['videos']} Vids)")
        
        from PySide6.QtWidgets import QTreeWidgetItem
        from PySide6.QtGui import QColor
        self.geometry_tree.clear()
        
        trail_root = QTreeWidgetItem(self.geometry_tree, ["Trails"])
        trail_root.setForeground(0, QColor("#10b981"))
        for t in parsed.get('trails', []):
            dist = t.get('distance_2d', 0)
            avg = t.get('avg_grade', 0)
            node = QTreeWidgetItem(trail_root, [f"{t['name']} ({dist:.0f}m, {avg:.1f}% grade)"])
            if 'filepath' in t: node.setData(0, Qt.UserRole, t['filepath'])
            
        pond_root = QTreeWidgetItem(self.geometry_tree, ["Ponds"])
        pond_root.setForeground(0, QColor("#3b82f6"))
        for p in pond_items:
            area = p.get('area_acres', 0)
            node = QTreeWidgetItem(pond_root, [f"{p['name']} ({area:.2f} acres)"])
            if 'filepath' in p: node.setData(0, Qt.UserRole, p['filepath'])
            
        cliff_root = QTreeWidgetItem(self.geometry_tree, ["Cliffs"])
        cliff_root.setForeground(0, QColor("#eab308"))
        for c in cliff_items:
            dist = c.get('distance_2d', 0)
            node = QTreeWidgetItem(cliff_root, [f"{c['name']} ({dist:.0f}m)"])
            if 'filepath' in c: node.setData(0, Qt.UserRole, c['filepath'])
            
        self.geometry_tree.expandAll()

    def refresh_media_list(self):
        """Re-initializes the UI List binding active SQLite stores."""
        from PySide6.QtWidgets import QListWidgetItem
        from core.db_manager import get_all_pois
        self.photo_list.clear()
        self.video_list.clear()
        pois = get_all_pois(self.current_location_id, self.current_start, self.current_end)
        for p in pois:
            filename = os.path.basename(p['filepath'])
            stem = os.path.splitext(filename)[0]
            display_text = stem
            if p['lat'] == 999.0:
                display_text = f"🚨[NEEDS GPS] {stem}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, p['id'])
            
            if p['type'] == 'photo':
                self.photo_list.addItem(item)
            else:
                self.video_list.addItem(item)
                
        self.refresh_measurements_list()
        self.refresh_regions_list()
                
    def refresh_measurements_list(self):
        from PySide6.QtWidgets import QListWidgetItem
        from core.db_manager import get_all_measurements
        self.measure_list.clear()
        for m in get_all_measurements(self.current_location_id):
            item = QListWidgetItem(m['name'])
            item.setData(Qt.UserRole, m['id'])
            self.measure_list.addItem(item)

    def delete_selected_measurement(self):
        from core.db_manager import delete_measurement
        sel_measure = self.measure_list.selectedItems()
        if not sel_measure: return
        uid = sel_measure[0].data(Qt.UserRole)
        delete_measurement(uid)
        self.refresh_measurements_list()
        self.map_view.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)

    def refresh_regions_list(self):
        from PySide6.QtWidgets import QListWidgetItem
        from core.db_manager import get_all_regions
        self.region_list.clear()
        for r in get_all_regions(self.current_location_id):
            item = QListWidgetItem(f"{r['name']} ({r['acres']:.2f} Acres)")
            item.setData(Qt.UserRole, r['id'])
            self.region_list.addItem(item)
            
    def delete_selected_region(self):
        from core.db_manager import delete_region
        sel_region = self.region_list.selectedItems()
        if not sel_region: return
        uid = sel_region[0].data(Qt.UserRole)
        delete_region(uid)
        self.refresh_regions_list()
        self.map_view.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)
        
    def export_pdf_map(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(self, "Export Property Map as PDF", "", "PDF Document (*.pdf)")
        if not path:
            return
            
        def pdf_printed(filepath, success):
            if success:
                msg = QMessageBox(self)
                msg.setWindowTitle("PDF Exported")
                msg.setText(f"<span style='color: white; font-size: 14px;'>Beautiful Property Map cleanly dumped to:<br>{filepath}</span>")
                msg.setStyleSheet("QMessageBox { background-color: #0f172a; } QLabel { color: white; } QPushButton { background-color: #3b82f6; color: white; border-radius: 4px; padding: 5px; }")
                msg.exec()
            else:
                print("Failed to print PDF")
                
        self.map_view.web_view.page().pdfPrintingFinished.connect(pdf_printed)
        self.map_view.web_view.page().printToPdf(path)

    def prompt_new_location(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Workspace Location")
        dlg.setStyleSheet("QDialog { background-color: #0f172a; } QLabel { color: white; font-weight: bold; } QLineEdit { background: #1e293b; color: white; border: 1px solid #334155; border-radius: 4px; padding: 6px; } QPushButton { background-color: #10b981; color: white; border-radius: 4px; padding: 5px 15px; font-weight: bold; } QPushButton#CancelBtn { background-color: #ef4444; }")
        
        layout = QVBoxLayout(dlg)
        
        layout.addWidget(QLabel("Workspace Name:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g. Backcountry Cabin")
        layout.addWidget(name_input)
        
        layout.addSpacing(10)
        
        layout.addWidget(QLabel("Map Center Latitude:"))
        lat_input = QLineEdit()
        lat_input.setPlaceholderText("e.g. 44.82702")
        layout.addWidget(lat_input)
        
        layout.addSpacing(10)
        
        layout.addWidget(QLabel("Map Center Longitude:"))
        lon_input = QLineEdit()
        lon_input.setPlaceholderText("e.g. -76.51533")
        layout.addWidget(lon_input)
        
        layout.addSpacing(15)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Location")
        btn_save.clicked.connect(dlg.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("CancelBtn")
        btn_cancel.clicked.connect(dlg.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        if dlg.exec():
            name = name_input.text().strip()
            lat_str = lat_input.text().strip()
            lon_str = lon_input.text().strip()
            
            if name and lat_str and lon_str:
                try:
                    lat = float(lat_str)
                    lon = float(lon_str)
                    from core.db_manager import insert_location
                    new_id = insert_location(name, lat, lon)
                    os.makedirs(os.path.join(self.proj_root, "project_data", "locations", str(new_id), "gpx"), exist_ok=True)
                    self.refresh_locations_dropdown()
                    # Auto select new location
                    for i in range(self.loc_dropdown.count()):
                        if self.loc_dropdown.itemData(i) == new_id:
                            self.loc_dropdown.setCurrentIndex(i)
                            break
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed placing location: {e}")

    def prompt_delete_location(self):
        curr_id = self.current_location_id
        if curr_id == 1:
            QMessageBox.warning(self, "Cannot Delete", "The default 'Home' Workspace cannot be deleted.")
            return
            
        reply = QMessageBox.question(self, "Delete Workspace", f"Are you sure you want to permanently delete Workspace ID #{curr_id} and ALL of its associated photos, measurements, and map layers?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            from core.db_manager import delete_location
            try:
                delete_location(curr_id)
                import shutil
                target_dir = os.path.join(self.proj_root, "project_data", "locations", str(curr_id))
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                
                # Switch cleanly to Default Home and refresh
                self.current_location_id = 1
                self.refresh_locations_dropdown()
                self.on_location_changed(self.loc_dropdown.currentIndex())
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to drop workspace recursively: {e}")

    def on_location_changed(self, index):
        loc_id = self.loc_dropdown.itemData(index)
        if loc_id:
            self.current_location_id = loc_id
            self.current_start = None
            self.current_end = None
            self.season_box.blockSignals(True)
            self.year_box.blockSignals(True)
            self.season_box.setCurrentIndex(0)
            self.year_box.setCurrentIndex(0)
            self.season_box.blockSignals(False)
            self.year_box.blockSignals(False)
            
            self.refresh_stats()
            self.refresh_media_list()
            self.map_view.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)

    def refresh_locations_dropdown(self):
        from core.db_manager import get_all_locations
        self.loc_dropdown.blockSignals(True)
        self.loc_dropdown.clear()
        locs = get_all_locations()
        for loc in locs:
            self.loc_dropdown.addItem(loc['name'], loc['id'])
            if loc['id'] == getattr(self, 'current_location_id', 1):
                self.loc_dropdown.setCurrentIndex(self.loc_dropdown.count() - 1)
        self.loc_dropdown.blockSignals(False)

    def delete_selected_geometry(self):
        """Drops physical OS boundaries exclusively from the Tree payload."""
        sel_geom = self.geometry_tree.selectedItems()
        if not sel_geom: return
        filepath = sel_geom[0].data(0, Qt.UserRole)
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                self.refresh_stats()
                self.map_view.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)
            except Exception as e:
                QMessageBox.warning(self, "Delete Failed", f"Could not explicitly drop native bounds: {e}")

    def delete_selected_media(self):
        """Drops SQLite records securely upon request."""
        from core.db_manager import get_poi, delete_poi

        selected = self.photo_list.selectedItems() + self.video_list.selectedItems()
        if not selected:
            return
            
        item = selected[0]
        poi_id = item.data(Qt.UserRole)
        poi_data = get_poi(poi_id)
        
        if poi_data:
            filepath = poi_data['filepath']
            
            # Sub-Thumbnail path removal algorithm natively
            if poi_data['type'] == 'photo':
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath) # Remove Thumbnail
                        
                    # Also wipe original high-res photo file securely mapping the basename natively
                    root_photo = os.path.join(self.proj_root, "project_data", "photos", os.path.basename(filepath))
                    if os.path.exists(root_photo):
                        os.remove(root_photo)
                except Exception as e:
                    print(f"Failed to remove photo file: {e}")
            elif poi_data['type'] == 'video':
                # Video file is the actual massive string reference
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    print(f"Failed to remove video file: {e}")
                    
            # Wipe backend and UI
            delete_poi(poi_id)
            self.refresh_media_list()
            
            # Immediately trigger isolated MapEngine reload flushing javascript dependencies securely
            self.map_view.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)
            self.refresh_stats()
            self.btn_measure.setChecked(False)

    def assign_selected_media(self):
        from core.db_manager import get_poi
        selected = self.photo_list.selectedItems() + self.video_list.selectedItems()
        if not selected: return
        poi_id = selected[0].data(Qt.UserRole)
        poi_data = get_poi(poi_id)
        if poi_data and poi_data['lat'] == 999.0:
            self.map_view.start_location_assignment(poi_id)
        else:
            QMessageBox.information(self, "GPS Intact", "This asset is already mapped!")

    def rename_selected_media(self):
        from core.db_manager import get_poi, update_poi_filepath, update_measurement_name
        from PySide6.QtWidgets import QInputDialog
        
        sel_measure = self.measure_list.selectedItems()
        if sel_measure:
            uid = sel_measure[0].data(Qt.UserRole)
            current_name = sel_measure[0].text()
            
            dialog = QInputDialog(self)
            dialog.setWindowTitle("Rename Measurement")
            dialog.setLabelText("Enter new line designation:")
            dialog.setTextValue(current_name)
            dialog.setStyleSheet("QDialog { background-color: #0f172a; } QLabel { color: white; font-weight: bold; } QLineEdit { background: #1e293b; color: white; border: 1px solid #334155; border-radius: 4px; padding: 4px; } QPushButton { background-color: #3b82f6; color: white; border-radius: 4px; padding: 5px 15px; }")
            
            ok = dialog.exec()
            new_name = dialog.textValue() if ok else None
            
            if ok and new_name and new_name != current_name:
                update_measurement_name(uid, new_name)
                self.refresh_measurements_list()
                self.map_view.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)
            return
    def rename_selected_geometry(self):
        """Hijacks Native payload OS files seamlessly dynamically."""
        from PySide6.QtWidgets import QInputDialog
        sel_geom = self.geometry_tree.selectedItems()
        if not sel_geom: return
        
        filepath = sel_geom[0].data(0, Qt.UserRole)
        if filepath and os.path.exists(filepath):
            current_dir = os.path.dirname(filepath)
            current_stem, current_ext = os.path.splitext(os.path.basename(filepath))
            dialog = QInputDialog(self)
            dialog.setWindowTitle("Rename Geometry Layer")
            dialog.setLabelText("Enter new mapping limit identifier:")
            dialog.setTextValue(current_stem)
            dialog.setStyleSheet("QDialog { background-color: #0f172a; } QLabel { color: white; font-weight: bold; } QLineEdit { background: #1e293b; color: white; border: 1px solid #334155; border-radius: 4px; padding: 4px; } QPushButton { background-color: #3b82f6; color: white; border-radius: 4px; padding: 5px 15px; }")
            
            ok = dialog.exec()
            new_stem = dialog.textValue() if ok else None
            
            if ok and new_stem and new_stem != current_stem:
                new_path = os.path.join(current_dir, new_stem + current_ext)
                if os.path.exists(new_path):
                    QMessageBox.warning(self, "Conflict", "Physical boundary string collides directly locally.")
                    return
                try:
                    os.rename(filepath, new_path)
                    self.refresh_stats()
                    self.map_view.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)
                except Exception as e:
                    QMessageBox.warning(self, "Rename Failed", f"Failed shifting geometric limits: {e}")

        selected = self.photo_list.selectedItems() + self.video_list.selectedItems()
        if not selected: return
        
        poi_id = selected[0].data(Qt.UserRole)
        poi_data = get_poi(poi_id)
        if not poi_data: return
        
        current_path = poi_data['filepath']
        current_dir = os.path.dirname(current_path)
        current_name = os.path.basename(current_path)
        current_stem, current_ext = os.path.splitext(current_name)
        
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Rename Media")
        dialog.setLabelText("Enter new filename:")
        dialog.setTextValue(current_stem)
        dialog.setStyleSheet("QDialog { background-color: #0f172a; } QLabel { color: white; font-weight: bold; } QLineEdit { background: #1e293b; color: white; border: 1px solid #334155; border-radius: 4px; padding: 4px; } QPushButton { background-color: #3b82f6; color: white; border-radius: 4px; padding: 5px 15px; }")
        
        ok = dialog.exec()
        new_stem = dialog.textValue() if ok else None
        
        if ok and new_stem and new_stem != current_stem:
            new_name = new_stem + current_ext
            new_path = os.path.join(current_dir, new_name)
            
            if os.path.exists(new_path):
                QMessageBox.warning(self, "Duplicate Name", "A file with this name already exists in the project data!")
                return
                
            try:
                os.rename(current_path, new_path)
                update_poi_filepath(poi_id, new_path)
                self.refresh_media_list()
                
                # Regenerate the map to reflect new path and UI
                self.map_view.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)
            except Exception as e:
                self.show_styled_msg("Rename Failed", f"Could not rename file natively: {e}", "critical")

    def export_csv_data(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save CSV Data", "supamap_export.csv", "CSV Files (*.csv)")
        if filepath:
            from core.export_handler import export_csv
            if export_csv(filepath):
                self.show_styled_msg("Export Successful", f"Successfully exported media database to:\n{filepath}", "info")
            else:
                self.show_styled_msg("Export Failed", "There was an error exporting or no media exists!", "warning")

    def export_kml_data(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save KML Map", "supamap_full_system.kml", "KML Files (*.kml)")
        if filepath:
            from core.export_handler import export_kml
            try:
                export_kml(filepath)
                self.show_styled_msg("Export Successful", f"Successfully exported full Topographic Map to:\n{filepath}", "info")
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.show_styled_msg("Export Failed", f"Failed to generate KML cleanly: {e}", "critical")

    def upload_photo(self):
        """Routine triggered from the UI button to select via OS."""
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Photo", "", "Images (*.jpg *.jpeg)")
        if not filepath:
            return
            
        # Parse and resize via background media handler
        try:
            target_thumb, lat, lon, heading, timestamp_str = process_and_save_upload(filepath)
            
            if lat is None:
                lat, lon = 999.0, 999.0
                
            # Log to DB
            poi_id = insert_poi(
                location_id=self.current_location_id,
                poi_type='photo', 
                filepath=target_thumb, 
                lat=lat, 
                lon=lon, 
                heading=heading,
                timestamp=timestamp_str
            )
            
            import base64
            
            def get_b64(filepath):
                if not os.path.exists(filepath): return ""
                with open(filepath, "rb") as f:
                    return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")
                    
            b64_img = get_b64(target_thumb)
            filename = os.path.basename(target_thumb)
            heading_str = f"Heading: {heading:.1f}&deg;" if heading else "Heading: N/A"
            notes = ""
            rotation = 0
            
            popup_html = f"""
            <div style="font-family: sans-serif; text-align: center; width: 150px;">
                <div style="width: 150px; height: 150px; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px auto;">
                    <img id="photo_{poi_id}" src='{b64_img}' style="max-width: 150px; max-height: 150px; border-radius: 4px; transform: rotate({rotation}deg); transition: transform 0.2s ease-in-out;">
                </div>
                <div style="font-size: 11px;"><b>{filename}</b></div>
                <div style="font-size: 10px; color: gray;">{timestamp_str}</div>
                <div style="font-size: 10px; margin-bottom: 5px;">{heading_str}</div>
                <hr style="margin:4px 0;">
                <textarea id="note_{poi_id}" placeholder="Type note here..." style="width: 140px; height: 50px; font-size: 11px; resize: none;">{notes}</textarea><br>
                <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                    <button style="font-size:10px; cursor:pointer; flex: 1; margin-right: 2px;" onclick="window.location.href='supabridge://save_note?id={poi_id}&note=' + encodeURIComponent(document.getElementById('note_{poi_id}').value)">Save Note</button>
                    <button style="font-size:10px; cursor:pointer; flex: 1; margin-left: 2px;" onclick="window.location.href='supabridge://rotate_photo?id={poi_id}'">Rotate ↻</button>
                </div>
            </div>
            """
                
            # Drop visually onto the active WebEngine instance instantly
            self.map_view.add_photo_marker(lat, lon, popup_html)
            self.refresh_media_list()
            self.refresh_stats()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.show_styled_msg("Import Error", f"Failed to process media: {e}", "critical")

    def upload_video(self):
        """Routine triggered from the UI button to select via OS."""
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Videos (*.mov *.mp4)")
        if not filepath:
            return
            
        try:
            target_vid, lat, lon, heading, timestamp_str = process_and_save_video_upload(filepath)
            
            if lat is None:
                lat, lon = 999.0, 999.0
                
            poi_id = insert_poi(
                location_id=self.current_location_id,
                poi_type='video', 
                filepath=target_vid, 
                lat=lat, 
                lon=lon, 
                heading=heading,
                timestamp=timestamp_str
            )
            
            filename = os.path.basename(target_vid)
            # Create supalocal path properly (ensure absolute resolves if queried, but LocalFileHandler accepts full abs path)
            abs_vid = os.path.abspath(target_vid).replace("\\", "/")
            if not abs_vid.startswith("/"):
                abs_vid = "/" + abs_vid
            # Grab thumbnail natively mapping OpenCV outputs!
            import base64
            def get_b64(filepath):
                if not os.path.exists(filepath): return ""
                with open(filepath, "rb") as f:
                    return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")
                    
            thumb_path = os.path.join(self.proj_root, "project_data", "thumbnails", filename + ".jpg")
            b64_img = get_b64(thumb_path)
            
            if b64_img:
                vid_box_style = f"width: 150px; height: 150px; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px auto; cursor: pointer; background: url('{b64_img}') center/cover; border-radius: 4px; border: 1px solid #334155; transition: 0.2s;"
                vid_inner = '<div style="background: rgba(15, 23, 42, 0.7); width: 40px; height: 40px; border-radius: 20px; display: flex; align-items: center; justify-content: center;"><span style="font-size: 24px; color: #10b981;">▶</span></div>'
            else:
                vid_box_style = "width: 150px; height: 100px; display: flex; align-items: center; justify-content: center; margin: 0 auto 5px auto; cursor: pointer; background: #0f172a; border-radius: 4px; border: 1px solid #334155; transition: 0.2s;"
                vid_inner = '<span style="font-size: 24px; color: #3b82f6;">▶</span><br><span style="color: #94a3b8; font-size: 10px; margin-left: 5px;">Play Video</span>'

            # HTML Layout mimicking photo but mapping HTML5 video natively preventing base64 bloat
            popup_html = f"""
            <div style="font-family: sans-serif; text-align: center; width: 150px;">
                <div style="{vid_box_style}" onclick="window.location.href='supabridge://play_video?id={poi_id}'">
                    {vid_inner}
                </div>
                <div style="font-size: 11px;"><b>{filename}</b></div>
                <div style="font-size: 10px; color: gray;">{timestamp_str[:16]}</div>
                <hr style="margin:4px 0;">
                <textarea id="note_{poi_id}" placeholder="Type note here..." style="width: 140px; height: 50px; font-size: 11px; resize: none;"></textarea><br>
                <div style="display: flex; justify-content: center; margin-top: 5px;">
                    <button style="font-size:10px; cursor:pointer;" onclick="window.location.href='supabridge://save_note?id={poi_id}&note=' + encodeURIComponent(document.getElementById('note_{poi_id}').value)">Save Note</button>
                </div>
            </div>
            """
            self.map_view.add_photo_marker(lat, lon, popup_html)
            self.refresh_media_list()
            self.refresh_stats()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.show_styled_msg("Import Error", f"Failed to process video: {e}", "critical")

    def upload_specific_gpx(self, category):
        filepath, _ = QFileDialog.getOpenFileName(self, f"Select {category.capitalize()} layer", "", "GPX Files (*.gpx)")
        if not filepath: return
        import shutil
        target_dir = os.path.join(self.proj_root, "project_data", "locations", str(self.current_location_id), "gpx", category)
        os.makedirs(target_dir, exist_ok=True)
        new_path = os.path.join(target_dir, os.path.basename(filepath))
        
        if os.path.exists(new_path):
            self.show_styled_msg("Conflict", "A map layer with this exact name already exists!", "warning")
            return
            
        try:
            shutil.copy2(filepath, new_path)
            self.refresh_stats()
            self.map_view.load_map(os.path.join(self.proj_root, "project_data"), self.current_start, self.current_end, location_id=self.current_location_id)
        except Exception as e:
            self.show_styled_msg("Import Failed", f"Could not explicitly mirror boundary: {e}", "critical")
                
    def show_styled_msg(self, title, text, msg_type="info"):
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(f"<span style='color: white; font-size: 13px;'>{text}</span>")
        msg.setStyleSheet("QMessageBox { background-color: #0f172a; border: 1px solid #334155; } QLabel { color: white; } QPushButton { background-color: #3b82f6; color: white; border-radius: 4px; padding: 5px 15px; font-weight: bold; }")
        
        if msg_type == "info":
            msg.setIcon(QMessageBox.Information)
        elif msg_type == "warning":
            msg.setIcon(QMessageBox.Warning)
        elif msg_type == "critical":
            msg.setIcon(QMessageBox.Critical)
            
        msg.exec()
                
    def _create_toggle_lambda(self, category, checkbox):
        """Creates an isolated connection lambda pointing directly to this checkbox state."""
        return lambda state: self.map_view.toggle_layer(category, checkbox.isChecked())

    def load_stylesheet(self):
        """Loads external CSS to establish the sleek dynamic interface."""
        style_path = os.path.join(self.bundle_root, "assets", "style.css")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
