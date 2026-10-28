"""Full pipeline: download -> counts -> synthetic tests -> league test -> bat-speed link -> charts -> Excel."""
import subprocess
import sys

STEPS = ["src/pull_data.py", "src/build_counts.py", "tests/test_synthetic.py",
         "src/persistence_test.py", "tests/test_batspeed_link.py", "src/batspeed_to_results.py",
         "src/validate.py", "src/make_charts.py", "src/build_tracker.py"]
for step in STEPS:
    print(f"\n=== {step} ===", flush=True)
    subprocess.run([sys.executable, step], check=True)
