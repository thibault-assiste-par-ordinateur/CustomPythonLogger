from setuptools import setup, find_packages
from pathlib import Path

HERE = Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name='custompythonlogger',
    version='1.0',
    packages=find_packages(),
    include_package_data=True,  # Include non-code files
    package_data={
        'custompythonlogger.config': ['logging.json'],
    },

    author="Thibault Arnoul",
    author_email="thibault-assiste-par-ordinateur@protonmail.com",
    description="custom utf8 python logging",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/thibault-assiste-par-ordinateur/CustomPythonLogger",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
