"""
abriTAMR --- AMR Gene Detection for MDU
"""
from sys import exit, version_info
from setuptools import setup, find_packages
from os import environ
import logging
import abritamr

# logging.basicConfig(level=environ.get("LOGLEVEL", "INFO"))

# if version_info <= (3, 0):
#     logging.fatal("Sorry, requires Python 3.x, not Python 2.x\n")
#     exit(1)


with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="abritamr",
    version=abritamr.__version__,
    description="Running AMRFinderPlus for MDU",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MDU-PHL/abritamr",
    author="Kristy Horan",
    author_email="kristyhoran15@gmail.com",
    maintainer="Kristy Horan",
    maintainer_email="kristyhoran15@gmail.com",
    python_requires=">=3.7, <4",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    zip_safe=False,
    install_requires=["snakemake", "pandas", "click", "jinja2"],
    test_suite="nose.collector",
    tests_require=["nose", "pytest"],
    entry_points={
        "console_scripts": [
            # "mdu-amr-detection=abritamr.abritamr:main",
            "abritamr=abritamr.abritamr:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: Implementation :: CPython",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    package_data={"abritamr": ["templates/*", "db/*", "utils/*", "test/*"]}
)
