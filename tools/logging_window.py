from collections import defaultdict, deque
import os
import re
import subprocess
import sys


class LoggingWindow:

    def __init__(self, header="", prefix="| ", max_lines=9999):
        self.original = sys.stdout
        self.max_lines = max_lines
        self.ellipsis_added = False
        self.window = deque(maxlen=max_lines)
        self.prefix = prefix
        self.height = 0
        if header:
            print("\033[1m" + header + "\033[0m")

        try:
            os.get_terminal_size()
            self.headless = False
        except:
            self.headless = True

    def __enter__(self):
        sys.stdout = self
        def run_subprocess(command, cwd=os.curdir, env=None, check=True):
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            stdout, stderr = ([], [])
            last_output = defaultdict(str)
            break_outer = False
            while True:
                for dst, stream in [(stdout, proc.stdout), (stderr, proc.stderr)]:
                    output = stream.readline()
                    last_output[stream] = output
                    if all(last_output[s] == '' for s in [proc.stdout, proc.stderr]) and proc.poll() is not None:
                        break_outer = True
                        break
                    if output:
                        self.write(output)
                        dst.append(output)
                if break_outer:
                    break

            rem_stdout, rem_stderr = proc.communicate()
            if rem_stdout:
                self.write(rem_stdout)
                stdout.append(rem_stdout)
            if rem_stderr:
                self.write(rem_stderr)
                stderr.append(rem_stderr)

            return stdout, stderr

        return run_subprocess

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original

    def fileno(self):
        return self.original.fileno()

    def write(self, message):
        if message == os.linesep: # Usually come from python prints, we can ignore
            return
        lines = message.rstrip(os.linesep).split(os.linesep)

        if self.headless:
            for line in lines:
                self.original.write(self.prefix + line + os.linesep)
            return

        for _ in range(self.height):
            self.original.write("\x1b[1A")  # Move cursor up by one line
        if len(self.window) == self.max_lines and len(lines) > 0 and not self.ellipsis_added:
            self.original.write('\x1b[2K')
            self.original.write(self.prefix + "...\n")
            self.ellipsis_added = True

        previous_height = self.height
        self.height = 0
        self.window.extend(lines)

        for line in self.window:
            self.original.write('\x1b[2K')
            line_to_write = self.prefix + line
            rendered_length = len(re.sub(r'\x1B[@-_][0-?]*[ -/]*[@-~]', '', line_to_write))
            try:
                line_height = (rendered_length // os.get_terminal_size().columns) + 1
            except:
                line_height = 1

            for _ in range(min((previous_height - self.height), line_height) - 1):
                self.original.write("\n")
                self.original.write('\x1b[2K')

            for _ in range(min((previous_height - self.height), line_height) - 1):
                self.original.write("\x1b[1A")  # Move cursor up by one line

            self.height += line_height
            self.original.write(self.prefix + line + os.linesep)

        if self.height < previous_height:
            for _ in range(previous_height - self.height):
                self.original.write('\x1b[2K')
                self.original.write("\n")
            for _ in range(previous_height - self.height):
                self.original.write("\x1b[1A")

    def flush(self):
        self.original.flush()


if __name__ == "__main__":
    with LoggingWindow("ls command") as run_subprocess:
        stdout, stderr = run_subprocess(["ls", "-l"])
        print(stdout)
