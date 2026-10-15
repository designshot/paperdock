"""Command line entrypoint; run with python3 -m paperdock."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import webbrowser


def main():
    parser = argparse.ArgumentParser(description='PaperDock — lokale Scan-App für Linux')
    parser.add_argument('--port', type=int, default=8756, help='Lokaler Port (Standard: 8756; 0 = automatisch)')
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'paperdock')
    parser.add_argument('--no-browser', action='store_true', help='Oberfläche nicht automatisch öffnen')
    parser.add_argument('--desktop', action='store_true', help='Eigenes GTK/WebKit-Fenster verwenden, falls installiert')
    parser.add_argument('--demo', action='store_true', help='Beim Start einen gekennzeichneten Beispielstapel anlegen')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('Port muss zwischen 0 und 65535 liegen.')
    os.umask(0o077)
    try:
        from .server import Application, Server, AppError
    except ModuleNotFoundError as exc:
        if exc.name == 'PIL':
            parser.exit(1, 'Pillow fehlt. Unter Ubuntu/Pop!_OS: sudo apt install python3-pil sane-utils\nAlternativ: python3 -m pip install . in einer virtuellen Umgebung.\n')
        raise
    try:
        app = Application(args.data_dir)
    except AppError as exc:
        parser.exit(1, str(exc) + '\n')
    try:
        server = Server(('127.0.0.1', args.port), app)
    except OSError as exc:
        app.shutdown()
        parser.exit(1, f'Lokaler App-Server konnte nicht gestartet werden: {exc}\nTipp: --port 0 wählt einen freien Port.\n')
    if args.demo:
        app.new_job({'demo': True})
    print(f'PaperDock läuft auf {server.origin}', flush=True)
    print('Zum Beenden Strg+C drücken. Daten bleiben lokal gespeichert.', flush=True)
    try:
        if args.desktop and not args.no_browser:
            wrapper = Path(__file__).with_name('desktop.py')
            interpreters = dict.fromkeys([sys.executable, shutil.which('python3'), '/usr/bin/python3'])
            for interpreter in filter(None, interpreters):
                check = subprocess.run([interpreter, str(wrapper), '--check'], capture_output=True)
                if check.returncode == 0:
                    threading.Thread(target=server.serve_forever, daemon=True).start()
                    subprocess.run([interpreter, str(wrapper), server.origin])
                    server.shutdown()
                    return
            print('GTK/WebKit nicht verfügbar; öffne im Standardbrowser.', flush=True)
        if not args.no_browser:
            threading.Timer(0.3, lambda: webbrowser.open(server.origin)).start()
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nPaperDock wird beendet.', flush=True)
    finally:
        app.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
