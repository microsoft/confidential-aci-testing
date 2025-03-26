from typing import Tuple
import os

# This has to be a separate module to avoid circular imports


def find_bicep_files(
    target_path: str,
) -> Tuple[str, str]:
    """
    Returns (bicep_file_path, bicepparam_file_path)
    """

    bicep_file_path = None
    bicepparam_file_path = None

    # Find the bicep files
    for file in os.listdir(target_path):
        if file.endswith(".bicep"):
            if bicep_file_path:
                raise ValueError("Multiple .bicep files found in the target directory.")
            bicep_file_path = os.path.join(target_path, file)
        elif file.endswith(".bicepparam"):
            if bicepparam_file_path:
                raise ValueError("Multiple .bicepparam files found in the target directory.")
            bicepparam_file_path = os.path.join(target_path, file)

    if not bicep_file_path:
        raise FileNotFoundError(f"No bicep file found in {target_path}")
    if not bicepparam_file_path:
        raise FileNotFoundError(f"No bicepparam file found in {target_path}")

    return bicep_file_path, bicepparam_file_path
