"""Genera el recurso de version del .exe para PyInstaller (--version-file).

SignPath exige que el ejecutable declare nombre de producto y version.
Uso: python version_info.py <salida>
"""
import sys

from version import VERSION

PRODUCT = "Peripheral Battery"
nums = tuple(int(x) for x in VERSION.split(".")) + (0,) * (4 - len(VERSION.split(".")))

TEMPLATE = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'MarcoVilera'),
      StringStruct('FileDescription', '{PRODUCT}'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'PeripheralBattery'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 MarcoVilera. MIT License.'),
      StringStruct('OriginalFilename', 'PeripheralBattery.exe'),
      StringStruct('ProductName', '{PRODUCT}'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

if __name__ == "__main__":
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        f.write(TEMPLATE)
