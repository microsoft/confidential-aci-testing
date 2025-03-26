from typing import List, Optional
import subprocess
import time


def run_cmd(cmd: List[str], retries: int = 0, consume_stdout: bool = True) -> Optional[str]:
    retried_times = 0
    while True:
        print(f"Running command: {' '.join(cmd)}")
        try:
            run_res = subprocess.run(cmd, stdout=subprocess.PIPE if consume_stdout else None, text=True, check=True)
            if consume_stdout:
                return run_res.stdout.strip()
            return None
        except subprocess.CalledProcessError as e:
            print(f"Command failed with code: {e.returncode}")
            retried_times += 1
            if retried_times <= retries:
                time.sleep(5)
            else:
                raise
