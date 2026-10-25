# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('kenshi_quick_translator/default_glossary.json', 'kenshi_quick_translator'), ('kenshi_quick_translator/icone.ico', 'kenshi_quick_translator'), ('kenshi_quick_translator/icone.png', 'kenshi_quick_translator')]
binaries = []
hiddenimports = ['kenshi_quick_translator.gui', 'tkinter', 'PIL.ImageTk']
tmp_ret = collect_all('kenshi_translator_toolkit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['iniciar.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='KenshiQuickTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['kenshi_quick_translator/icone.ico'],
)
