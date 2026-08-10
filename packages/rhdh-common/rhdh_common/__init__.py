"""Shared runtime for RHDH skill scripts.

Import submodules directly so that no import pulls in a dependency the caller
did not ask for:

    from rhdh_common.output import OutputFormatter
    from rhdh_common.process import find_acli, run_command
    from rhdh_common.jsonio import error_exit, log
    from rhdh_common.versions import ver_sort_key

``rhdh_common.openshift_release.yaml`` is the only module that needs a
non-stdlib dependency; it is gated behind the ``yaml`` extra.
"""

__version__ = "0.1.0"
