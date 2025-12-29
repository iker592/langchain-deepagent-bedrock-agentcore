import os

from setuptools import find_packages, setup

PACKAGE_NAME = "yahoo-dsp-agent-sdk"
PYPI_PACKAGE_NAME = f"{PACKAGE_NAME}"
PACKAGE_VERSION = os.getenv("PACKAGE_VERSION")

setup(
    name=PYPI_PACKAGE_NAME,
    version=PACKAGE_VERSION,
    description="Yahoo DSP Agent SDK - A framework for building AI agents with Strands",
    license="Apache License 2.0",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Yahoo DSP Squad Optimus",
    author_email="team-optimus@yahooinc.com",
    url="https://git.ouryahoo.com/ads-data/agent-sdk",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "yahoo_dsp_agent_sdk": [
            "**/*.json",
            "**/*.txt",
            "**/*.md",
            "**/*.yml",
            "**/*.yaml",
            "**/*.toml",
            "**/*.cfg",
            "**/*.ini",
            "**/*.properties",
            "**/*.html",
            "**/*.css",
            "**/*.sh",
        ],
    },
    install_requires=[
        "strands-agents>=1.7.0",
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    keywords="ai, agents, strands, sdk, dsp, yahoo",
)
