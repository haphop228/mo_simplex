import PyInstaller.__main__
import os
import platform

# Determine the separator for pyinstaller based on OS
sep = ';' if platform.system() == 'Windows' else ':'

# Build the application
PyInstaller.__main__.run([
    'main.py',
    '--name=SimplexSolver',
    '--windowed',
    '--onefile',
    f'--add-data=ui{sep}ui'
])
