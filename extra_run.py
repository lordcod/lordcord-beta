import sys
import subprocess


venv_python = sys.executable
process = subprocess.Popen([venv_python, "run.py"], executable=venv_python)


try:
    while process.poll() is None:
        pass
finally:
    sys.exit()
