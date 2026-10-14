"""Run memory-backed RPC boundary checks; skip prohibited extra loopback server."""
import runpy
import unittest

if __name__ == '__main__':
    module = runpy.run_path('line-3/tools/rpc-boundary/check.py')
    tests = module['BoundaryTests']
    tests.test_actual_http_redirect_refused = unittest.skip(
        'Assignment permits only the supplied local RPC address')(tests.test_actual_http_redirect_refused)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(tests))
    raise SystemExit(0 if result.wasSuccessful() else 1)
