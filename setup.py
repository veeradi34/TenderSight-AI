#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="tender-agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain-openai>=0.3.24",
        "langchain>=0.3.26",
        "langchain-community>=0.3.26",
        "langchain-text-splitters>=0.3.8",
        "playwright>=1.52.0",
        "python-dotenv>=1.1.0",
        "streamlit>=1.38.0",
        "pydantic>=2.0.0",
        "requests>=2.32.4",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "tender-agent=main:main_tender_agent",
        ],
    },
)
