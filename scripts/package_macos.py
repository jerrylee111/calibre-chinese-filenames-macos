#!/usr/bin/env python3
"""Package the calibre 9.17.0 filename patch without changing the inputs."""

import argparse
import ast
import hashlib
import pathlib
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def prepare_source(source, dest):
    tree = ast.parse((source / 'src/calibre/constants.py').read_text())
    version = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'numeric_version' for t in node.targets))
    if version != (9, 17, 0):
        raise ValueError('This reference supports calibre 9.17.0 only')
    shutil.copytree(source / 'src', dest / 'src', ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
    shutil.copytree(source / 'bypy/macos', dest / 'bypy/macos')
    for name in ('LICENSE', 'COPYRIGHT'):
        shutil.copy2(source / name, dest / name)
    backend = dest / 'src/calibre/db/backend.py'
    text = backend.read_text()
    pairs = (
        ('        author = ascii_filename(author)[:l]', '        #author = ascii_filename(author)[:l]'),
        ('        title = ascii_filename(title.lstrip())[:l].rstrip()', '        #title = ascii_filename(title.lstrip())[:l].rstrip()'),
    )
    for original, patched in pairs:
        lines = text.splitlines()
        if lines.count(original) == 2 and lines.count(patched) == 0:
            text = text.replace(original, patched)
        elif lines.count(patched) != 2 or lines.count(original) != 0:
            raise ValueError('Unexpected backend.py: check the filename patch against your source')
    backend.write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=pathlib.Path)
    parser.add_argument('--base-app', required=True, type=pathlib.Path)
    parser.add_argument('--output', required=True, type=pathlib.Path)
    args = parser.parse_args()
    if platform.system() != 'Darwin':
        parser.error('Packaging requires macOS and Apple Command Line Tools')
    output = args.output.resolve()
    if output.exists():
        parser.error('The output already exists; choose a new filename')
    for tool in ('clang', 'codesign', 'ditto', 'xattr', 'hdiutil'):
        if not shutil.which(tool):
            parser.error(f'Missing required tool: {tool}')
    source, base = args.source.resolve(), args.base_app.resolve()
    if base.name != 'calibre.app':
        parser.error('--base-app must point to the official calibre.app')
    with (base / 'Contents/Info.plist').open('rb') as f:
        info = plistlib.load(f)
    if info.get('CFBundleShortVersionString') != '9.17.0':
        parser.error('The base app must also be calibre 9.17.0')
    scripts = pathlib.Path(__file__).resolve().parent
    # Keep signing outside cloud-synced folders: FinderInfo can invalidate it.
    with tempfile.TemporaryDirectory(prefix='calibre-chinese-package-') as tmp:
        tmp = pathlib.Path(tmp)
        prepared = tmp / 'source'
        prepare_source(source, prepared)
        stage = tmp / 'image'
        stage.mkdir()
        app = stage / 'calibre.app'
        run('ditto', '--norsrc', '--noextattr', base, app)
        run(sys.executable, scripts / 'build_app.py', prepared, app)
        (stage / 'Applications').symlink_to('/Applications')
        shutil.copy2(scripts.parent / 'README.md', stage / 'README.md')
        output.parent.mkdir(parents=True, exist_ok=True)
        run('hdiutil', 'create', '-volname', 'calibre 中文文件名版 9.17.0',
            '-srcfolder', stage, '-format', 'UDZO', '-imagekey', 'zlib-level=6', output)
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.with_suffix(output.suffix + '.sha256').write_text(f'{digest}  {output.name}\n')
    print(f'Created: {output}')


if __name__ == '__main__':
    main()
