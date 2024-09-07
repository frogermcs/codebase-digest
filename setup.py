from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="codeconsolidator",
    version='0.1.4',  # This will be automatically updated by the script
    author="Kamil Stanuch",
    description="Consolidates and analyzes codebases for insights.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kamilstanuch/CodebaseConsolidator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords="code analysis, codebase, consolidation, visualization",
    install_requires=[
        "tiktoken",
        "colorama",
    ],
    entry_points={
        "console_scripts": [
            "codeconsolidator=codeconsolidator.app:main",
        ],
    },
    python_requires='>=3.6',
    include_package_data=True,
)