# Confidential WCOW support

This document describes how `c-aci-testing` supports **Confidential WCOW**
(Windows containers on SNP-protected UVMs) in addition to the existing
LCOW path.

## Why

The `vm runc` / `vm generate_scripts` pipeline was originally hardcoded
for LCOW:

- runtime `runhcs-lcow`
- pod annotation `io.microsoft.virtualmachine.lcow.securitypolicy`
- pod template including `linux.security_context` and the
  `lcow.hcl-enabled` annotation
- liveness check via `sh -c 'echo ...; sleep 1'`
- `bash` as the default interactive shell

For C-WCOW these all differ. The trigger is `osType: 'Windows'` on the
bicep's container group.

## What changed

### New files

```
src/c_aci_testing/templates/wcow_configs/
    container_group.json.template
    container.json.template
    pull.json.template
```

The WCOW pod template uses the **`wcow.*`** annotation set (NOT `lcow.*`):

```json
"annotations": {
  "io.microsoft.virtualmachine.wcow.isolation_type": "SecureNestedPaging",
  "io.microsoft.virtualmachine.wcow.writable_efi": "true",
  "io.microsoft.virtualmachine.wcow.enforcer": "rego",
  "io.microsoft.virtualmachine.wcow.securitypolicy": "<SECURITY_POLICY>"
}
```

The WCOW container template has no `linux.security_context` /
`forwardPorts`. The WCOW pull template uses `sandbox-platform: windows/amd64`.

### `tools/vm_generate_scripts.py:make_configs`

Per container group, detect `osType` and select:

| Aspect | LCOW | WCOW |
|---|---|---|
| Template dir | `templates/lcow_configs/` | `templates/wcow_configs/` |
| Runtime | `runhcs-lcow` | `runhcs-wcow-hypervisor` |
| Security policy annotation | `io.microsoft.virtualmachine.lcow.securitypolicy` | `io.microsoft.virtualmachine.wcow.securitypolicy` |
| Liveness check shell | `sh -c 'echo X; sleep 1'` | `cmd.exe /c 'echo X & timeout /t 1 > nul'` |
| Default `connect.ps1` argv | `bash` | `cmd.exe` |
| `dmesg` log stream | enabled | omitted (no Linux dmesg) |
| `linux.security_context.privileged` passthrough | enabled | omitted |
| `pull.json` sandbox-platform | `linux/amd64` | `windows/amd64` |

The `win_flavor == "ws2022"` special case (deletes the `lcow.hcl-enabled`
annotation) only applies to LCOW pods and is gated `(not is_wcow)`.

### Bug fixes folded into the same PR

1. **`utils/parse_bicep.py`** now resolves `variables()` ARM expressions.
   Bicep usually inlines `var` references at build time, but emits
   `[variables('name')]` when a `var` appears inside another ARM
   expression (e.g. `if(empty(...), variables('x'), variables('x'))`).
   Without this handler, the call fell through to the unknown-function
   branch and ended up as a literal string, breaking confcom.

2. **`tools/aci_param_set.py`** no longer double-joins `target_path`.
   `find_bicep_files` already returns paths joined with `target_path`,
   so the second join produced `target_path/target_path/file.bicepparam`
   when `target_path` was relative. Absolute paths masked the bug via
   `os.path.join` semantics.

## What is intentionally NOT changed yet

- **`vm_runc` itself** still calls `vm_create` to provision a fresh VM.
  Reusing an existing VM (e.g. a dev box with the confidential
  cri-containerd cplat already installed) requires adding a path that
  skips `vm_create` when the VM is supplied externally. Out of scope
  here ΓÇö defer.
- **`policies_gen.py`** is unchanged. `az confcom acipolicygen` already
  dispatches WCOW vs LCOW from the ARM template's `osType` field.
- **Windows `subprocess` / `shutil.which` resolution.** On Windows,
  `subprocess.run(["az", ...])` cannot resolve bare command names that
  rely on PATHEXT (e.g. `az.cmd`). The fix is to wrap each call site,
  which is ~27 files and is best done as a separate PR.

## Verifying

The `confidential-aci-dashboard` repo has a `workloads/minimal_cwcow`
workload that exercises the full path:

1. The bicep declares `osType:'Windows'`, `sku:'Confidential'`,
   `ccePolicy: ccePolicies.minimal_cwcow`.
2. The bicepparam ships with a pre-populated permissive policy.
3. `c-aci-testing vm generate_scripts` emits CRI configs with the
   `wcow.*` annotations, `runp.ps1` using `runhcs-wcow-hypervisor`, and
   `pull.json` with `windows/amd64`.
4. Those configs run via `azcrictl` on a Windows host with the
   confidential cri-containerd cplat installed.
