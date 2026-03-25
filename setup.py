"""
Setup configuration for ot-miner package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="ot-miner",
    version="0.1.0",
    description="Two-pass GitHub issue scenario miner for Open Targets platform testing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Open Targets",
    url="https://github.com/opentargets/ot-github-issue-miner",
    license="Apache License 2.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.31.0",
        "langchain>=0.1.0",
        "langchain-anthropic>=0.1.0",
        "langchain-core>=0.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ot-miner=ot_miner.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords=[
        "bioinformatics",
        "open-targets",
        "github",
        "scenario-mining",
        "test-data",
    ],
)
