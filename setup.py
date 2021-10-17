import io

from setuptools import find_packages, setup

with io.open("fable_py/version.py", encoding="utf-8") as fid:
    for line in fid:
        if line.startswith("__version__"):
            __version__ = line.strip().split()[-1][1:-1]
            break

with open("README.md") as f:
    readme = f.read()

setup(
    name="fable_py",
    version=__version__,
    description="A Fable (python) kernel for Jupyter",
    long_description=readme,
    author="Dag Brattli",
    author_email="dag@brattli.net",
    url="https://github.com/dbrattli/Fable.Jupyter",
    install_requires=["jupyter"],
    dependency_links=[],
    packages=find_packages(include=["fable_py"]),
    package_data={"fable_py": ["images/*.png"]},
    classifiers=[
        "Framework :: IPython",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: FSharp",
        "Topic :: System :: Shells",
    ],
)
