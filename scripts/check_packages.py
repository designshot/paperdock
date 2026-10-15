"""Check release artifacts without unpacking or executing their contents."""
from pathlib import Path
import sys
import tarfile
import zipfile


def check(directory):
    wheels = list(directory.glob('paperdock_local-*.whl'))
    sources = list(directory.glob('paperdock_local-*.tar.gz'))
    if not wheels or not sources:
        raise SystemExit('Expected a PaperDock wheel and source distribution.')
    for path in wheels:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            for filename in ('static/index.html', 'static/styles.css', 'static/app.js',
                             'static/theme.js', 'orientation.py', 'document_names.py'):
                assert 'paperdock/' + filename in names, (path, filename)
            for filename in ('LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md'):
                assert any(name.endswith('/' + filename) for name in names), (path, filename)
            assert archive.testzip() is None, path
            assert not any('/drivers/' in name or name.endswith('.so') for name in names), path
    for path in sources:
        with tarfile.open(path) as archive:
            names = [entry.name.partition('/')[2] for entry in archive.getmembers()]
            for filename in ('install.sh', 'bootstrap.sh', 'NOTICE', 'THIRD_PARTY_NOTICES.md',
                             'docs/INSTALL.md', 'drivers/scansnap-wifi/build.py',
                             'drivers/scansnap-wifi/COPYING', 'paperdock/static/theme.js'):
                assert filename in names, (path, filename)
            assert not any(name.startswith(('work/', 'jobs/', '.git/')) or
                           name.endswith(('settings.json', 'preferences.json', '.so'))
                           for name in names), path
    print('Source distribution and wheel contain the required code and notices.')


if __name__ == '__main__':
    check(Path(sys.argv[1] if len(sys.argv) > 1 else 'dist'))
