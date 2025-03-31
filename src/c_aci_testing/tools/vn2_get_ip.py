#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

from __future__ import annotations
import json
import time
import sys

from c_aci_testing.utils.run_cmd import run_cmd


def vn2_get_ip(deployment_name: str, timeout: int = 300, **kwargs):
    """
    Wait for the service load balancer to be ready and return its external IP.

    Args:
        deployment_name: Name of the deployment/service
        timeout: Maximum time to wait in seconds (default: 300)

    Returns:
        str: The external IP of the service
    """
    print(f"Waiting for external IP on service/{deployment_name} (timeout: {timeout}s)", file=sys.stderr, flush=True)

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            service_json = run_cmd(["kubectl", "get", "service", deployment_name, "-o", "json"], retries=2, log_run_to=sys.stderr)
            assert service_json
            service_data = json.loads(service_json)

            # Check if the service has an external IP assigned
            external_ip = None
            if "status" in service_data and "loadBalancer" in service_data["status"]:
                ingress = service_data["status"]["loadBalancer"].get("ingress", [])
                if ingress and "ip" in ingress[0]:
                    external_ip = ingress[0]["ip"]

            if external_ip:
                print(external_ip, flush=True)
                return external_ip

            time.sleep(5)

        except Exception as e:
            if "NotFound" in str(e):
                print(f"Service {deployment_name} not found, waiting...", file=sys.stderr, flush=True)
                time.sleep(5)
            else:
                print(f"Error retrieving service information: {e}", file=sys.stderr, flush=True)
                time.sleep(5)

    print(f"service/{deployment_name} did not get an external IP within {timeout} seconds.", file=sys.stderr, flush=True)
    sys.exit(1)
