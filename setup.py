#!/usr/bin/env python
"""
Legacy setup.py to force pip to use old-style installation
This bypasses PEP 517/518 and setuptools.build_meta entirely
"""

from setuptools import setup, find_packages

setup(
    name="cryptouniverse-enterprise",
    version="1.0.0",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "pydantic==2.5.1",
        "python-dotenv==1.0.0",
    ],
)
