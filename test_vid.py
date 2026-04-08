from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtCore import QUrl
import sys
from main import register_custom_schemes, LocalFileHandler

app = QApplication(sys.argv)
register_custom_schemes()
handler = LocalFileHandler()
QWebEngineProfile.defaultProfile().installUrlSchemeHandler(b"supalocal", handler)

page = QWebEnginePage()
page.loadFinished.connect(lambda ok: print(f"Load finished: {ok}") or app.quit())
page.setHtml("<video src='supalocal:///d:/test.mp4'></video>")
app.exec()
