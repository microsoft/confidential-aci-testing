#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------


from __future__ import annotations

import argparse
import os

from .subparsers.aci import subparse_aci
from .subparsers.env import subparse_env
from .subparsers.github import subparse_github
from .subparsers.images import subparse_images
from .subparsers.infra import subparse_infra
from .subparsers.policies import subparse_policies
from .subparsers.target import subparse_target
from .subparsers.vm import subparse_vm
from .subparsers.vscode import subparse_vscode
from .subparsers.vn2 import subparse_vn2


def parse_command():

    arg_parser = argparse.ArgumentParser(
        "Utilities for testing workflows involving Confidential ACI."
    )

    subparser = arg_parser.add_subparsers(dest="command", required=True)
    
    # Set up all subcommands immediately so help works properly
    aci_parser = subparser.add_parser("aci", help="Azure Container Instances commands")
    env_parser = subparser.add_parser("env", help="Environment management commands") 
    github_parser = subparser.add_parser("github", help="GitHub workflow commands")
    infra_parser = subparser.add_parser("infra", help="Infrastructure management commands")
    images_parser = subparser.add_parser("images", help="Container image commands")
    policies_parser = subparser.add_parser("policies", help="Policy management commands")
    target_parser = subparser.add_parser("target", help="Target management commands")
    vm_parser = subparser.add_parser("vm", help="Virtual machine commands")
    vscode_parser = subparser.add_parser("vscode", help="VSCode integration commands")
    vn2_parser = subparser.add_parser("vn2", help="VN2 commands")
    
    # Set up all subcommands upfront
    subparse_aci(aci_parser)
    subparse_env(env_parser) 
    subparse_github(github_parser)
    subparse_infra(infra_parser)
    subparse_images(images_parser)
    subparse_policies(policies_parser)
    subparse_target(target_parser)
    subparse_vm(vm_parser)
    subparse_vscode(vscode_parser)
    subparse_vn2(vn2_parser)

    import sys
    
    # Check for common insufficient argument patterns
    if len(sys.argv) == 1:
        # No arguments at all
        arg_parser.print_help()
        exit(0)
    elif len(sys.argv) == 2 and sys.argv[1] in ['aci', 'env', 'github', 'infra', 'images', 'policies', 'target', 'vm', 'vscode', 'vn2']:
        # Just a command with no subcommand
        command = sys.argv[1]
        parser_map = {
            'aci': aci_parser,
            'env': env_parser, 
            'github': github_parser,
            'infra': infra_parser,
            'images': images_parser,
            'policies': policies_parser,
            'target': target_parser,
            'vm': vm_parser,
            'vscode': vscode_parser,
            'vn2': vn2_parser
        }
        parser_map[command].print_help()
        exit(0)
        
    args = arg_parser.parse_args()

    missing_args = []
    exceptions = ["repository", "tag", "infrastructure_svn", "yaml_path", "deploy_output_file"]
    for key, value in vars(args).items():
        if value is None and key not in exceptions:
            missing_args.append(key)

    if missing_args:
        raise argparse.ArgumentError(
            None, os.linesep.join(f"--{key.replace('_', '-')} is required" for key in missing_args)
        )

    return args
