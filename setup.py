#!/usr/bin/env python3
"""
Setup script for JARVIS voice assistant.
"""

from setuptools import setup, find_packages
from pathlib import Path

project_root = Path(__file__).parent
long_description = (project_root / "README.md").read_text(encoding="utf-8")

setup(
    name="jarvis-voice-assistant",
    version="3.0",
    author="Nelson",
    description="Local voice assistant for Windows with Portuguese language support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/jarvis",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/jarvis/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Intended Audience :: End Users/Desktop",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.12",
    install_requires=[
        "SpeechRecognition>=3.10.0",
        "pyaudio>=0.2.13",
        "edge-tts>=6.1.12",
        "pygame>=2.5.2",
        "pycaw>=20231128",
        "google-api-python-client>=1.12.0",
        "google-auth-oauthlib>=1.2.0",
        "google-auth-httplib2>=0.2.0",
    ],
    entry_points={
        "console_scripts": [
            "jarvis=jarvis.app:main",
        ],
        "gui_scripts": [
            "jarvis-gui=jarvis.app:main",
        ],
    },
)
