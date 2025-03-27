from typing import List
import subprocess
import time

def run_cmd(cmd: List[str], retries: int = 0):
    retried_times = 0
    while True:
        print(f"Running command: {' '.join(cmd)}")
        try:
            return subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True).stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Command failed with code: {e.returncode}")
            retried_times += 1
            if retried_times <= retries:
                time.sleep(5)
            else:
                raise
