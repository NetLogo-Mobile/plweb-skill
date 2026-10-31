"""Load only physicslab local-model modules, without running its network imports."""
import importlib
import sys
from pathlib import Path

def load_local_modules():
    vendor=Path(__file__).resolve().parents[1]/'vendor'
    if not (vendor/'physicslab/__init__.py').is_file():raise RuntimeError('Bundled modeling library is missing; reinstall this skill bundle')
    if 'physicslab' in sys.modules:
        current=Path(sys.modules['physicslab'].__file__).resolve()
        if not current.is_relative_to(vendor.resolve()):raise RuntimeError('Start a fresh Python process to use the bundled library')
    else:
        sys.path.insert(0,str(vendor))
        importlib.import_module('physicslab')
    local={name:importlib.import_module('physicslab.'+name) for name in ('coordinate_system','enums','circuit','celestial','electromagnetism')}
    return local
