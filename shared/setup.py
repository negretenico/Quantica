from setuptools import setup, find_packages

setup(
    name="quantica-shared",
    version="0.0.1",
    packages=["shared", *[f"shared.{p}" for p in find_packages()]],
    package_dir={"shared": "."},
    install_requires=["pika>=1.3.0", "requests>=2.31.0"],
)
