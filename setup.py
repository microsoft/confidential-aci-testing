from setuptools import setup, find_packages

setup(
    name="c-aci-testing",
    version="0.1.11",
    description="Utilities for testing workflows involving Confidential ACI.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Dominic Ayre",
    author_email="dominicayre@microsoft.com",
    url="https://github.com/microsoft/c-aci-testing",
    packages=find_packages(),
    install_requires=[
        "pytest",
        "json5",
    ],
    include_package_data=True,
    package_data={
        "": [
            "./test/example/*",
            "./aci/*",
            "./.vscode/*",
            "./python_runner/*",
            "./github_actions/*",
        ],
    },
)
