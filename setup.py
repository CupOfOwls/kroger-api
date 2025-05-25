from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="kroger-api",
    version="0.1.0",
    packages=find_packages(exclude=['tests*', 'docs_kroger_api*', 'venv*', 'examples*', 'assets*']),
    
    # Dependencies
    install_requires=[
        "requests>=2.25.0",
        "python-dotenv>=0.15.0",
        "certifi>=2021.0.0",
        "urllib3>=1.26.0",
    ],
    
    # Optional dependencies for development/examples
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-mock>=3.0.0',
            'requests-mock>=1.9.0',
            'black',
            'flake8',
            'mypy',
        ],
        'examples': [
            'tabulate>=0.8.0',
        ],
    },
    
    # Metadata
    author="Stephen Thoemmes",
    author_email="thoemmes.stephen@gmail.com",
    description="A Python client library for the Kroger Public API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="kroger, api, grocery, shopping, retail",
    url="https://github.com/CupOfOwls/kroger-api",
    project_urls={
        "Bug Reports": "https://github.com/CupOfOwls/kroger-api/issues",
        "Source": "https://github.com/CupOfOwls/kroger-api",
        "Kroger API Documentation": "https://developer.kroger.com/documentation/public/",
        "Demo Video": "https://github.com/CupOfOwls/kroger-api/blob/main/assets/kroger-api-python-add-to-cart-demo.mp4",
    },
    
    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Office/Business",
    ],
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Include additional files (controlled by MANIFEST.in)
    include_package_data=True,
    zip_safe=False,
)