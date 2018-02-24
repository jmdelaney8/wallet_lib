"""wallet_lib python package configuration."""

from setuptools import setup

setup(
    name='wallet_lib',
    version='0.1.0',
    packages=[
        'wallet_lib',
    ],
    include_package_data=True,
    install_requires=[
        'pycoin==0.80'
    ],
)
