"""Structural rules of the project that should never be broken by accident."""

import subprocess
import sys


def test_physics_modules_do_not_load_the_interface():
    """The numerical side must be usable without Qt: importing it may not pull in PySide6."""
    code = (
        "import sys\n"
        "import bhlab, bhlab.constants, bhlab.units, bhlab.formatting\n"
        "import bhlab.physics.newtonian, bhlab.solvers.fixed_step\n"
        "import bhlab.physics.orbital_elements, bhlab.solvers.adaptive, bhlab.orbit\n"
        "import bhlab.simulation.model\n"
        "loaded = sorted(name for name in sys.modules if name.startswith('PySide6'))\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
