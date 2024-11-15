#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from .args.parser import parse_command


def main():
    args = parse_command()

    if args.command == "env":

        if args.env_command == "create":
            from .tools.env_create import env_create

            env_create(**vars(args))

        else:
            print(f"env command: {args.env_command} not recognised")

    elif args.command == "infra":

        if args.infra_command == "deploy":
            from .tools.infra_deploy import infra_deploy

            infra_deploy(**vars(args))

        else:
            print(f"infra command: {args.infra_command} not recognised")

    elif args.command == "target":

        if args.target_command == "create":
            from .tools.target_create import target_create

            target_create(**vars(args))

        elif args.target_command == "run":
            from .tools.target_run import target_run

            target_run(**vars(args))

        elif args.target_command == "add_test":
            from .tools.target_add_test import target_add_test

            target_add_test(**vars(args))

        else:
            print(f"target command: {args.target_command} not recognised")

    elif args.command == "images":

        if args.images_command == "build":
            from .tools.images_build import images_build

            images_build(**vars(args))

        elif args.images_command == "push":
            from .tools.images_push import images_push

            images_push(**vars(args))

        elif args.images_command == "pull":
            from .tools.images_pull import images_pull

            images_pull(**vars(args))

        else:
            print(f"images command: {args.images_command} not recognised")

    elif args.command == "policies":

        if args.policies_command == "gen":
            from .tools.policies_gen import policies_gen

            policies_gen(**vars(args))

        else:
            print(f"policies command: {args.policies_command} not recognised")

    elif args.command == "aci":

        if args.aci_command == "get":
            if args.get_command == "ids":
                from .tools.aci_get_ids import aci_get_ids

                print(aci_get_ids(**vars(args)))

            elif args.get_command == "is_live":
                from .tools.aci_get_is_live import aci_get_is_live

                print(aci_get_is_live(**vars(args)))

            elif args.get_command == "ips":
                from .tools.aci_get_ips import aci_get_ips

                print(aci_get_ips(**vars(args)))

            else:
                print(f"aci get command: {args.get_command} not recognised")

        elif args.aci_command == "monitor":
            from .tools.aci_monitor import aci_monitor

            aci_monitor(**vars(args))

        elif args.aci_command == "deploy":
            from .tools.aci_deploy import aci_deploy

            aci_deploy(**vars(args))

        elif args.aci_command == "param_set":
            from .tools.aci_param_set import aci_param_set

            aci_param_set(**vars(args))

        elif args.aci_command == "remove":
            from .tools.aci_remove import aci_remove

            aci_remove(**vars(args))

        else:
            print(f"aci command: {args.aci_command} not recognised")

    elif args.command == "vm":

        if args.vm_command == "create":
            from .tools.vm_create import vm_create

            vm_create(**vars(args))

        elif args.vm_command == "create_noinit":
            from .tools.vm_create_noinit import vm_create_noinit

            vm_create_noinit(**vars(args))

        elif args.vm_command == "generate_scripts":
            from .tools.vm_generate_scripts import vm_generate_scripts

            vm_generate_scripts(**vars(args))

        elif args.vm_command == "runc":
            from .tools.vm_runc import vm_runc

            vm_runc(**vars(args))

        elif args.vm_command == "check":
            from .tools.vm_check import vm_check

            vm_check(**vars(args))

        elif args.vm_command == "deploy":
            from .tools.vm_deploy import vm_deploy

            vm_deploy(**vars(args))

        elif args.vm_command == "remove":
            from .tools.vm_remove import vm_remove

            vm_remove(**vars(args))

        elif args.vm_command == "get":
            if args.get_command == "ids":
                from .tools.aci_get_ids import aci_get_ids

                print(aci_get_ids(**vars(args)))

            else:
                print(f"aci get command: {args.get_command} not recognised")

        elif args.vm_command == "cp_into":
            from .tools.vm_cp_into import vm_cp_into

            vm_cp_into(**vars(args))

        elif args.vm_command == "exec":
            from .tools.vm_exec import vm_exec

            vm_exec(**vars(args))

        elif args.vm_command == "cat":
            from .tools.vm_cat import vm_cat

            vm_cat(**vars(args))

        elif args.vm_command == "cache_cplat":
            from .tools.vm_cache_cplat import vm_cache_cplat

            vm_cache_cplat(**vars(args))

        else:
            print(f"vm command: {args.vm_command} not recognised")

    elif args.command == "vscode":

        if args.vscode_command == "run_debug":
            from .tools.vscode_run_debug import vscode_run_debug

            vscode_run_debug(**vars(args))

        else:
            print(f"vscode command: {args.vscode_command} not recognised")

    elif args.command == "github":

        if args.github_command == "workflow":
            from .tools.github_workflow import github_workflow

            github_workflow(**vars(args))

        else:
            print(f"github command: {args.github_command} not recognised")

    else:
        print(f"Command: {args.command} not recognised")


if __name__ == "__main__":
    main()
