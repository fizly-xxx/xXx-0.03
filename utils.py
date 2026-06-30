import os
import sys

def get_ui_path():
    """Шукає вшиту папку ui у тимчасовій директорії розпаковки Nuitka"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'ui', 'index.html')

def get_jsons_dir():
    """Пошук папки jsons поруч із .exe (навіть у режимі Onefile)"""
    if '__compiled__' in globals() or getattr(sys, 'frozen', False):
        # sys.argv[0] у Windows для Nuitka вказує на шлях до запущеного EXE
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(base_dir, 'jsons')