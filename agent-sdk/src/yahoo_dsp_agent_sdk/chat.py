import os
import subprocess
import sys


def main():
    script_path = os.path.join(os.path.dirname(__file__), "scripts", "chat.sh")
    subprocess.run([script_path] + sys.argv[1:])


if __name__ == "__main__":
    main()
