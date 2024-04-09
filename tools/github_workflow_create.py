#!/usr/bin/env python3


import argparse
import os

import subprocess

from tools.target_find_files import find_bicep_file


def github_workflow_create(target):

    if not os.path.exists(target):
        print("Target doesn't exist")
        return

    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).strip().decode()
    user_workflows_dir = os.path.join(repo_root, ".github", "workflows")

    if not os.path.exists(user_workflows_dir):
        os.mkdir(user_workflows_dir)

    workflow_file = os.path.join(os.path.dirname(__file__), "github_actions", "example.yml")

    with open(workflow_file, "r") as file:
        workflow = file.read()

    test_name = os.path.splitext(find_bicep_file(target))[0]
    workflow = workflow.replace("<TARGET_PATH>", os.path.relpath(target, repo_root))
    workflow = workflow.replace("Test Example", f'Test {test_name.replace("_", " ").title()}')
    workflow = workflow.replace("test-example", f'test-{test_name.replace("_", "-")}')

    workflow_file_name = f"test_{test_name}.yml"
    workflow_file_path = os.path.join(user_workflows_dir, workflow_file_name)
    with open(workflow_file_path, "w") as file:
        file.write(workflow)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add python test target to target")

    parser.add_argument("target",
        help="Target directory", default=os.environ.get("TARGET"),
        nargs="?", # aka Optional
        type=lambda path: os.path.abspath(os.path.expanduser(path)))

    args = parser.parse_args()

    github_workflow_create(args.target)
