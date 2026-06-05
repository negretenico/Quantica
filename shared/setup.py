from setuptools import setup, find_packages

setup(
    name="quantica-shared",
    version="0.0.1",
    packages=find_packages(),
    install_requires=["pika>=1.3.0"],
)
