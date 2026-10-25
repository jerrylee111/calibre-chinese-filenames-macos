#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Reuses calibre upstream launcher.c and util.h (Kovid Goyal and contributors).
import ast
import pathlib
import plistlib
import shutil
import subprocess
import sys
import tempfile

source = pathlib.Path(sys.argv[1]).resolve()
app = pathlib.Path(sys.argv[2]).resolve()
root = pathlib.Path(tempfile.mkdtemp(prefix='calibre-chinese-launchers-'))
contents = app / 'Contents'
embedded = contents / 'Resources' / 'ChineseSource'
shutil.copytree(source / 'src', embedded / 'src', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
shutil.copy2(source / 'LICENSE', embedded / 'LICENSE')
shutil.copy2(source / 'COPYRIGHT', embedded / 'COPYRIGHT')
constants = embedded / 'src/calibre/constants.py'
constants.write_text(constants.read_text().replace(
    'is_running_from_develop = running_in_develop_mode()',
    'is_running_from_develop = False  # Packaged app: use the bundled prebuilt UI and web resources.'))

# Use the upstream launcher and ABI; select the source inside this bundle before
# its Python interpreter starts. The path is resolved afresh after every move.
launcher = (source / 'bypy/macos/launcher.c').read_text()
launcher = '#include <locale.h>\n' + launcher
launcher = launcher.replace('    run(PROGRAM,', '''    char source_path[sizeof(realpath_buf) + 128];
    char *last_slash = strrchr(path, '/');
    if (last_slash == NULL) fatal("Invalid executable path");
    snprintf(source_path, sizeof(source_path), "%.*s/../Resources/ChineseSource/src", (int)(last_slash - path), path);
    if (setenv("CALIBRE_DEVELOP_FROM", source_path, 1) != 0) fatal("Cannot select bundled source");
    setenv("PYTHONDONTWRITEBYTECODE", "1", 1);
    setlocale(LC_CTYPE, "en_US.UTF-8");
    run(PROGRAM,''')
(root / 'launcher.c').write_text(launcher)
shutil.copy2(source / 'bypy/macos/util.h', root / 'util.h')
tree = ast.parse((source / 'src/calibre/linux.py').read_text())
assignment = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'entry_points' for t in n.targets))
entries = eval(compile(ast.Expression(assignment.value), '<entry_points>', 'eval'), {'__appname__': 'calibre'})
for kind, items in entries.items():
    for item in items:
        program, target = map(str.strip, item.split('='))
        module, func = target.split(':')
        dest = contents / 'MacOS' / program
        dest.unlink()
        subprocess.run(['clang', '-arch', 'arm64', '-arch', 'x86_64', '-mmacosx-version-min=14.0', '-Os', '-Wall',
                        f'-DPROGRAM=L"{program}"', f'-DMODULE=L"{module}"', f'-DFUNCTION=L"{func}"',
                        f'-DIS_GUI={"true" if kind == "gui_scripts" else "false"}',
                        str(root / 'launcher.c'), str(contents / 'Frameworks/calibre-launcher.dylib'),
                        '-o', str(dest)], check=True)
        print('Built', program, flush=True)

plist_path = contents / 'Info.plist'
with plist_path.open('rb') as f:
    plist = plistlib.load(f)
plist['CFBundleDisplayName'] = 'calibre 中文文件名版'
plist['CalibreChineseFilenamePatch'] = '9.17.0; embedded source; original user patch'
with plist_path.open('wb') as f:
    plistlib.dump(plist, f)

entitlements = root / 'entitlements.plist'
with entitlements.open('wb') as f:
    plistlib.dump({k: True for k in ('com.apple.security.cs.allow-dyld-environment-variables',
                                   'com.apple.security.cs.allow-jit',
                                   'com.apple.security.cs.allow-unsigned-executable-memory')}, f)
subprocess.run(['xattr', '-cr', str(app)], check=True)
subprocess.run(['codesign', '--force', '--deep', '--sign', '-', '--entitlements', str(entitlements), str(app)], check=True)
subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
shutil.rmtree(root)
print('App signed locally and verified.', flush=True)
