"""
Test help functionality for c-aci-testing commands.

This test validates that help can be displayed at all command levels without
requiring Azure CLI configuration or login.
"""

import subprocess
import pytest


def test_main_help():
    """Test that main help can be displayed."""
    result = subprocess.run(
        ["c-aci-testing", "-h"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Utilities for testing workflows involving Confidential ACI" in result.stdout
    assert "aci" in result.stdout
    assert "Azure Container Instances commands" in result.stdout


def test_subcommand_help():
    """Test that subcommand help can be displayed."""
    result = subprocess.run(
        ["c-aci-testing", "aci", "-h"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "aci" in result.stdout
    assert "deploy" in result.stdout


def test_deep_subcommand_help():
    """Test that deep subcommand help can be displayed."""
    result = subprocess.run(
        ["c-aci-testing", "aci", "deploy", "-h"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "aci deploy" in result.stdout
    assert "--subscription" in result.stdout
    assert "target_path" in result.stdout


def test_no_command_shows_help():
    """Test that running without command shows usage."""
    result = subprocess.run(
        ["c-aci-testing"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert "the following arguments are required: command" in result.stderr


def test_insufficient_subcommand_shows_help():
    """Test that running with insufficient subcommand shows usage."""
    result = subprocess.run(
        ["c-aci-testing", "aci"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert "aci_command" in result.stderr


@pytest.mark.parametrize("command", [
    "env", "github", "infra", "images", "policies", "target", "vm", "vscode", "vn2"
])
def test_all_subcommands_help(command):
    """Test that all subcommands can display help."""
    result = subprocess.run(
        ["c-aci-testing", command, "-h"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert command in result.stdout