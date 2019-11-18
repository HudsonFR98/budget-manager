from setuptools import setup, find_packages

setup(
    name="{{ cookiecutter.app|upper }}",
    description='',
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
)