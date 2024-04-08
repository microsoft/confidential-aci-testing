#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import tempfile
import glob


def package_build():

    package_name = "c_aci_testing"

    # Create a temporary directory to assemble the package
    with tempfile.TemporaryDirectory() as tempdir:

        shutil.copy("README.md", tempdir)
        shutil.copy("setup.py", tempdir)

        package_dir = os.path.join(tempdir, package_name)
        
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)
        os.mkdir(package_dir)
        
        # Copy the contents of ./tools to the package directory
        for file in os.listdir("tools"):
            if file.endswith(".py"):
                shutil.copy(os.path.join("tools", file), package_dir)

        shutil.copytree("aci", os.path.join(package_dir, "aci"))
        shutil.copytree("test", os.path.join(package_dir, "test"))

        subprocess.run(["tree", package_dir])
        subprocess.run(["python", "setup.py", "sdist"], cwd=tempdir)
        for file in glob.glob(os.path.join(tempdir, "dist", "*.tar.gz")):
            shutil.copy(
                file, 
                os.path.realpath(os.path.join(os.path.basename(__file__), ".."))
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the python package")
    args = parser.parse_args()
    package_build()
