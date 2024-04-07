from setuptools import setup, find_packages

setup(
    name='c-aci-testing',
    version='0.1',
    description='Utilities for testing workflows involving Confidential ACI.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Dominic Ayre',
    author_email='dominicayre@microsoft.com',
    url='https://github.com/microsoft/c-aci-testing',
    packages=find_packages(),
    install_requires=[],
)