import sys
import os

def get_install_dir():
    """Returns the persistent physical directory where the executable or main.py lives.
    Used for storing Database SQL files and Project Data safely on the hard drive."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        # Resolve from core/system_paths.py up one level back to SupaMap root
        return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

def get_bundle_dir():
    """Returns the ephemeral internal directory where bundled assets sit (CSS, Maps).
    When frozen, PyInstaller dumps these transiently into a hidden temp folder."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
