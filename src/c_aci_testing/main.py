#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations

from .args.parser import parse


def main():
    args = parse()

    if args.command == "env":

        if args.env_command == "create":
            from .tools.env_create import env_create

            env_create(**vars(args))

    if args.command == "infra":

        if args.infra_command == "deploy":
            from .tools.infra_deploy import infra_deploy

            infra_deploy(**vars(args))

    if args.command == "target":

        if args.target_command == "create":
            from .tools.target_create import target_create

            target_create(**vars(args))

        if args.target_command == "run":
            from .tools.target_run import target_run

            target_run(**vars(args))

    if args.command == "images":

        if args.images_command == "build":
            from .tools.images_build import images_build

            images_build(**vars(args))

        if args.images_command == "push":
            from .tools.images_push import images_push

            images_push(**vars(args))

        if args.images_command == "pull":
            from .tools.images_pull import images_pull

            images_pull(**vars(args))

    if args.command == "policies":

        if args.policies_command == "gen":
            from .tools.policies_gen import policies_gen

            policies_gen(**vars(args))

    if args.command == "aci":

        if args.aci_command == "get":
            if args.get_command == "ids":
                from .tools.aci_get_ids import aci_get_ids

                print(aci_get_ids(**vars(args)))

            if args.get_command == "is_live":
                from .tools.aci_get_is_live import aci_get_is_live

                print(aci_get_is_live(**vars(args)))

            if args.get_command == "ips":
                from .tools.aci_get_ips import aci_get_ips

                print(aci_get_ips(**vars(args)))

        if args.aci_command == "monitor":
            from .tools.aci_monitor import aci_monitor

            aci_monitor(**vars(args))

        if args.aci_command == "deploy":
            from .tools.aci_deploy import aci_deploy

            aci_deploy(**vars(args))

        if args.aci_command == "param_set":
            from .tools.aci_param_set import aci_param_set

            aci_param_set(**vars(args))

        if args.aci_command == "remove":
            from .tools.aci_remove import aci_remove

            aci_remove(**vars(args))


if __name__ == "__main__":
    main()
