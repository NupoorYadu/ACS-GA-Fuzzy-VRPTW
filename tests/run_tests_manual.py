import sys
import traceback

import importlib.util
from pathlib import Path
import sys

# ensure project root is on sys.path so tests can import 'src'
proj_root = str(Path(__file__).resolve().parents[1])
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)


def load_test_func(path, func_name):
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, func_name)

ROOT = Path(__file__).parent
test_acs_func = load_test_func(ROOT / 'test_acs.py', 'test_acs_basic_solution')
test_plot_func = load_test_func(ROOT / 'test_plotting.py', 'test_plot_routes_creates_file')

failed = False

print('Running test_acs_basic_solution...')
try:
    test_acs_func()
    print('PASS')
except Exception as e:
    failed = True
    print('FAIL')
    traceback.print_exc()

print('\nRunning test_plot_routes_creates_file...')
try:
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    test_plot_func(tmp)
    print('PASS')
except Exception as e:
    failed = True
    print('FAIL')
    traceback.print_exc()

if failed:
    sys.exit(1)
else:
    sys.exit(0)
