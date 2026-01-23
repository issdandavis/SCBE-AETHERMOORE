"""
SCBE-AETHERMOORE Python SDK

Spectral Context-Bound Encryption + Hyperbolic Governance for AI-to-AI Communication
"""

from setuptools import setup, find_packages

setup(
    name="scbe-aethermoore",
    version="3.0.0",
    author="Issac Daniel Davis",
    author_email="issdandavis@gmail.com",
    description="Hyperbolic Governance for AI-to-AI Communication",
    long_description=open("../README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/issdandavis/scbe-aethermoore-demo",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security :: Cryptography",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.24.0",
        "cryptography>=41.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "hypothesis>=6.0.0",
        ],
        "pqc": [
            "liboqs-python>=0.7.0",
        ],
    },
)
