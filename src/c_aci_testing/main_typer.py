#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

"""Main entry point using Typer for CLI argument parsing."""

from __future__ import annotations

def main():
    """Main entry point with Typer-based CLI."""
    from .args.typer_parser import app
    app()


if __name__ == "__main__":
    main()