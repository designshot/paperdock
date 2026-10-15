"""Optional GTK 4 / WebKit 6 desktop shell; no Python-native bridge exposed."""
import sys
from urllib.parse import urlsplit

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('WebKit', '6.0')
    from gi.repository import Gtk, WebKit, Gio
except (ImportError, ValueError):
    sys.exit(2)

if '--check' in sys.argv:
    sys.exit(0)

origin = sys.argv[1] if len(sys.argv) > 1 else ''
parsed = urlsplit(origin)
if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port:
    sys.exit('Ungültige lokale App-Adresse.')


class PaperDockWindow(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='io.paperdock.App', flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.choosers = []
        self.connect('activate', self.activate_window)

    def activate_window(self, _):
        self.window = Gtk.ApplicationWindow(application=self, title='PaperDock')
        self.window.set_default_size(1440, 960)
        context = WebKit.WebContext.new()
        self.web = WebKit.WebView(web_context=context)
        self.web.get_settings().set_enable_developer_extras(False)
        self.web.connect('decide-policy', self.navigation)
        self.web.get_network_session().connect('download-started', self.download_started)
        self.window.set_child(self.web)
        self.web.load_uri(origin)
        self.window.present()

    def navigation(self, _, decision, kind):
        if kind in (WebKit.PolicyDecisionType.NAVIGATION_ACTION, WebKit.PolicyDecisionType.NEW_WINDOW_ACTION):
            uri = decision.get_navigation_action().get_request().get_uri()
            if not uri.startswith(origin + '/') and uri != origin:
                decision.ignore()
                return True
        return False

    def download_started(self, _, download):
        download.connect('decide-destination', self.choose_destination)

    def choose_destination(self, download, suggested):
        chooser = Gtk.FileChooserNative.new('PDF speichern', self.window, Gtk.FileChooserAction.SAVE, 'Speichern', 'Abbrechen')
        chooser.set_current_name(suggested or 'PaperDock.pdf')
        self.choosers.append(chooser)
        def respond(dialog, response):
            if response == Gtk.ResponseType.ACCEPT and dialog.get_file() and dialog.get_file().get_path():
                download.set_destination(dialog.get_file().get_path())
            else:
                download.cancel()
            dialog.destroy()
            self.choosers.remove(dialog)
        chooser.connect('response', respond)
        chooser.show()
        return True


PaperDockWindow().run([sys.argv[0]])
