#!/usr/bin/env python
"""
setup.py - script for building padulator

Usage:
    % python setup.py py2app
"""
from distutils.core import setup
import os
import shutil
import py2app
NAME='Padulator'

py2app_options = {
        'argv_emulation': False,
        'includes':['sip','PyQt5','PyQt5.QtCore','PyQt5.QtGui','requests','flowlayout'],
        'frameworks': ['/usr/local/Cellar/qt5/5.5.0/plugins/platforms/libqcocoa.dylib'],
        'packages':['requests'],
        'excludes':['scipy'],
        }

setup(
    app=['padulator.py'],
    name=NAME,
    options={'py2app':py2app_options},
    data_files = ['./orbs','qt.conf'],
    setup_requires=['py2app']
)

os.makedirs('dist/' + NAME + '.app/Contents/PlugIns/platforms', exist_ok=True)
shutil.copyfile('dist/' + NAME + '.app/Contents/Frameworks/libqcocoa.dylib',
        'dist/' + NAME + '.app/Contents/PlugIns/platforms/libqcocoa.dylib')
