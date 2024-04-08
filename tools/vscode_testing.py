#!/usr/bin/env python3


import argparse
import os
import shutil

import json
import json5


def vscode_run_debug(target):

    if not os.path.exists(target):
        print("Target doesn't exist")
        return
    
    # Copy the python runner code to the target
    runner_dir = os.path.join(os.path.dirname(__file__), "python_runner")
    for file in os.listdir(runner_dir):
        if file.endswith(".py"):
            shutil.copy(os.path.join(runner_dir, file), target)

    # If there isn't already a configuration file for pytest create one
    vs_code_path = os.path.join(os.curdir, ".vscode")
    if not os.path.exists(vs_code_path):
        os.mkdir(vs_code_path)

    user_json_path = os.path.join(vs_code_path, "settings.json")
    if not os.path.exists(user_json_path):
        shutil.copy(
            os.path.join(os.path.dirname(__file__), ".vscode", "settings.json"), 
            user_json_path
        )
        
        with open(user_json_path, "r") as file:
            user_json = json5.load(file)
        
        user_json["python.testing.unittestArgs"][2] = os.path.abspath(os.path.join(target, ".."))
        
        with open(user_json_path, "w") as file:
            json.dump(user_json, file, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add python test target to target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))

    args = parser.parse_args()

    vscode_run_debug(args.target)
