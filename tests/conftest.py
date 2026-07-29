"""server/ isn't a package on the default pytest path (its modules use bare
imports like `from _auth import ...`, matching how they're actually run -
see server/index.py's docstring), so route-level tests need it added
explicitly. Only test_auth.py (and future route-level test modules) need
this; the existing app/*-level tests never touch server/ at all."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
