# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for SideScrollerPython
# Run from the SideScrollerPython-main folder with:
#   pyinstaller game.spec

import os

block_cipher = None

a = Analysis(
    ['assets/source/main.py'],
    pathex=[os.path.abspath('assets/source')],  # so Python finds your local imports
    binaries=[],
    datas=[
        ('assets/sprites',  'assets/sprites'),
        ('assets/sounds',   'assets/sounds'),
        ('assets/maps',     'assets/maps'),
        ('assets/settings', 'assets/settings'),
    ],
    hiddenimports=['psutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SideScroller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # Set to True if you want a debug console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/sprites/misc/bug.ico",            # Add path to a .ico file here if you want a custom icon
)
