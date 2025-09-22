# small test runner to import update_checker
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('update_checker', str(Path(__file__).resolve().parents[1] / 'src' / 'update_checker.py'))
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)
print('IMPORT_OK')
