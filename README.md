# 🌍 SupaMap

**SupaMap** is a high-performance, locally-hosted Geographic Information System (GIS) application built explicitly for speed, privacy, and precision mapping. 

Featuring a fully integrated Multi-Tenant architecture, SupaMap acts as an incredibly robust workspace capable of dynamically mapping GPX boundaries, rendering native SQLite video structures utilizing OpenCV framing pipelines, and executing heavy geodesic footprint modeling straight from a visually stunning PySide6 dark mode interface.

---

## 🚀 Key Features

* 🔐 **Absolute Local Privacy:** SupaMap explicitly isolates and stores all Media Paths, Geodesic calculations, and Map Data natively offline using a relational `app_state.sqlite` structure. Zero external dependencies required.
* 📦 **Multi-Tenant Workspaces:** Track endless maps seamlessly isolating locations cleanly avoiding overlapping GPS leakage. Build boundary structures specifically tracking distinct environments natively securely.
* 📷 **Dynamic Native Media Engine:** Drag out photos or High Frame Rate `.mov`/`.mp4` videos safely tracking GPS metadata cleanly into your visual layer with OpenCV resolving thumbnail extraction accurately.
* 📏 **PyProj Geodesic Calculations:** Drop physical boundaries natively interacting completely dynamically in your UI while Python calculates extremely tight acreage and distance metrics utilizing PyProj's Ellipsoid Math natively tracking bounds.
* 🖨️ **High-Fidelity PDF Export:** The embedded QWebEngine Page maps exact bounding limits flawlessly bridging Vector elements right out natively directly resolving an aesthetic Property System PDF securely.

---

## 🛠️ Architecture Overview

The system bridges lightweight Javascript layers (Leaflet, Folium) securely resolving constraints implicitly avoiding bloat via custom `supabridge://` URL bindings tracking PySide endpoints. This creates an unparalleled level of fluidity securely preventing web-viewer stutter significantly.

**Backend Setup:**
* `PySide6` - Advanced native window boundary logic natively generating a custom UI layout smoothly safely.
* `Folium / Leaflet` - Visual constraints seamlessly loading GPX mapping cleanly!
* `OpenCV` - Encoding boundaries bridging mp4 structures inherently explicitly dynamically mapping tracking limits flawlessly!
* `PyProj / Shapely` - Acreage bounds mathematically isolated implicitly tracking mapping perfectly.


## 💻 How to Run

Running SupaMap directly from the cloned repository ensures you always have the latest architecture tracking correctly on your OS natively cleanly!

1. **Install Virtual Environment** (Highly Recommended)
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

2. **Install Local Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3. **Launch the Engine**
    ```bash
    python main.py
    ```

## 📦 Building an Executable

SupaMap is fully cross-platform and can be explicitly packaged into a strictly standalone application (requiring no Python installation for the end user) on both Windows and macOS natively!

**For Windows (`.exe`):**
Double-click the `build.bat` file in the root directory. It will generate a standalone `SupaMap.exe` application inside the `dist/` folder.

**For macOS (`.app`):**
Open your terminal and run:
```bash
sh build_mac.sh
```
It will automatically map the macOS Subprocess hooks and yield a fully native `SupaMap.app` packaged directly into your `dist/` folder!
