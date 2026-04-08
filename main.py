import sys
import os
from PySide6.QtWidgets import QApplication

# Ensure local imports work correctly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ui.main_window import MainWindow

def setup_app_folders():
    """Ensure essential base directories and data structures exist."""
    from core.system_paths import get_install_dir
    base_dir = get_install_dir()
    folders = [
        "data",
        "project_data/gpx",
        "project_data/photos",
        "project_data/videos",
        "project_data/thumbnails"
    ]
    for folder in folders:
        os.makedirs(os.path.join(base_dir, folder), exist_ok=True)
        
    # Database initialization hook
    from core.db_manager import init_db
    init_db()

from PySide6.QtWebEngineCore import QWebEngineUrlScheme, QWebEngineUrlSchemeHandler, QWebEngineProfile
from PySide6.QtCore import QFile, QIODevice

class LocalFileHandler(QWebEngineUrlSchemeHandler):
    def requestStarted(self, request):
        url = request.requestUrl()
        file_path = url.path()
        # Windows formatting fix for QUrl paths
        if file_path.startswith('/'):
            file_path = file_path[1:]
            
        file = QFile(file_path)
        if file.open(QIODevice.ReadOnly):
            ext = file_path.lower().split('.')[-1]
            mime_type = b"video/mp4" if ext in ['mp4', 'mov'] else b"image/jpeg"
            request.reply(mime_type, file)
        else:
            request.fail(request.Error.UrlNotFound)

def register_custom_schemes():
    scheme = QWebEngineUrlScheme(b"supalocal")
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.SecureScheme |
        QWebEngineUrlScheme.Flag.LocalScheme |
        QWebEngineUrlScheme.Flag.LocalAccessAllowed |
        QWebEngineUrlScheme.Flag.CorsEnabled
    )
    QWebEngineUrlScheme.registerScheme(scheme)

def main():
    # Scaffold initial property folders if this is a fresh launch
    setup_app_folders()
    
    # Must register Custom Scheme BEFORE Application boots
    register_custom_schemes()
    
    # Initialize the Qt Application
    app = QApplication(sys.argv)
    
    # Bind Handler
    handler = LocalFileHandler()
    QWebEngineProfile.defaultProfile().installUrlSchemeHandler(b"supalocal", handler)
    
    # Setup Main Window
    window = MainWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
