"""Independent suite wrapper; preserves the shared runner used by other attempts."""
import run_suite

run_suite.SUITES['stage3-integrity'] = ['derived/test_stage3_integrity.py']
if __name__ == '__main__':
    run_suite.main()
