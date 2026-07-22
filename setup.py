from setuptools import setup, find_packages

setup(
    name="hp-semiconductor-analyzer",
    version="1.0.0",
    description="GUI controller for HP 4145A/B, 4156A/B, and 4280A instruments via GPIB",
    author="Prashant – UCSB ECE",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "PyQt5>=5.15",
        "PyVISA>=1.13",
        "PyVISA-py>=0.7",
        "matplotlib>=3.7",
        "numpy>=1.24",
        "pandas>=2.0",
        "scipy>=1.10",
    ],
    entry_points={
        "console_scripts": [
            "hp-analyzer=main:main",
        ]
    },
)
