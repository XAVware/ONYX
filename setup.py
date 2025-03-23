from setuptools import setup, find_packages

setup(
    name="onyx",
    version="0.1.2",
    packages=find_packages(),
    install_requires=[
        "rich",
        "anthropic",
        "networkx",
        "click",
        "dotenv",
        "setuptools",
        "pyyaml",
        "mkdocs"
    ],
    author="Ryan Smetana",
    author_email="ryan.smetana@xavware.com",
    description="ONYX: AI-Powered iOS App Development Framework",
    keywords="iOS, development, AI",
    python_requires=">=3.7",
)