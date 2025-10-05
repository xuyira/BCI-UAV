#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for Hand-Eye Coordination Controller
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="hand-eye-coordination-controller",
    version="1.0.0",
    author="[Your Name]",
    author_email="[your.email@example.com]",
    description="A real-time hand-eye coordination control system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/hand-eye-coordination-controller",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "black>=21.0.0",
            "flake8>=3.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hand-eye-controller=main:main",
        ],
    },
    keywords="eye-tracking hand-gesture coordination control human-machine-interface",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/hand-eye-coordination-controller/issues",
        "Source": "https://github.com/yourusername/hand-eye-coordination-controller",
        "Documentation": "https://github.com/yourusername/hand-eye-coordination-controller#readme",
    },
)
