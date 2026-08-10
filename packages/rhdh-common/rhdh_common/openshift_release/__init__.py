"""Read openshift/release CI configuration from a checkout or from GitHub.

Namespaced deliberately: this is domain knowledge about one upstream
repository, not general-purpose utility code. Import the submodules directly —
``rhdh_common.openshift_release.yaml`` needs the ``yaml`` extra, and nothing
that only resolves a repository root should have to install it.
"""
