"""Setup для max_userapi"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="max-userapi",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Высокоуровневая Python-библиотека для работы с Max Messenger UserAPI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/max_userapi",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Communications :: Chat",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "Asmax>=0.1.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
    },
)

