"""Load only physicslab local-model modules, without running its network imports."""
import importlib
import importlib.util
import sys
import types

def load_local_modules():
    if 'physicslab' in sys.modules:
        raise RuntimeError('Run in a fresh Python process before importing physicslab.')
    spec=importlib.util.find_spec('physicslab')
    if spec is None or not spec.submodule_search_locations:
        raise ModuleNotFoundError('Install physicslab 3.0.0 in this Python environment first.')
    package=types.ModuleType('physicslab')
    package.__path__=list(spec.submodule_search_locations)
    package.__package__='physicslab'
    package.__spec__=spec
    sys.modules['physicslab']=package
    network=types.ModuleType('physicslab.web')
    class UnavailableUser:
        def __init__(self,*args,**kwargs):
            raise RuntimeError('Library network operations are disabled; use the verified community adapter.')
    network.User=UnavailableUser
    # Local experiment modules evaluate this unused network default at import time.
    # Supplying None avoids executing any library network module or login call.
    network.anonymous_login=lambda *args,**kwargs:None
    sys.modules['physicslab.web']=network
    local={name:importlib.import_module('physicslab.'+name) for name in ('coordinate_system','enums','circuit','celestial','electromagnetism')}
    return local
