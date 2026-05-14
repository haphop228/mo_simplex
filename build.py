"""Сборка независимого исполняемого файла через PyInstaller.

Канонический способ сборки — `python build.py`. Файл `SimplexSolver.spec`
БОЛЬШЕ НЕ ИСПОЛЬЗУЕТСЯ (см. баг #9): его поведение полностью покрыто
флагами CLI ниже. Если PyInstaller сгенерирует новый .spec в текущей
директории — он будет перезаписываться при следующем запуске сборки
и не должен коммититься в репозиторий.

Поддерживаемые платформы: Windows (.exe), macOS (.app), Linux (бинарник).
На macOS флаг `--windowed` автоматически собирает .app-бандл.
"""

import PyInstaller.__main__
import platform

# Определяем разделитель для --add-data в зависимости от ОС.
sep = ';' if platform.system() == 'Windows' else ':'

PyInstaller.__main__.run([
    'main.py',
    '--name=SimplexSolver',
    '--windowed',
    '--onefile',
    f'--add-data=ui{sep}ui',
    '--noconfirm',
])
