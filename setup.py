import io

from setuptools import find_packages, setup

with io.open('fable/version.py', encoding="utf-8") as fid:
    for line in fid:
        if line.startswith('__version__'):
            __version__ = line.strip().split()[-1][1:-1]
            break

with open('README.md') as f:
    readme = f.read()

setup(name='fable',
      version=__version__,
      description='A Fable (python) kernel for Jupyter based on MetaKernel',
      long_description=readme,
      author='Dag Brattli',
      author_email='dag@brattli.net',
      url="https://github.com/dbrattli/fsharp-fable",
      install_requires=["metakernel", "expression"],
      dependency_links=[
          "https://github.com/cognitedata/expression"
      ],
      packages=find_packages(include=["fable", "fable.*"]),
      package_data={'fable': ["images/*.png", "modules/*.ss"]},
      classifiers=[
          'Framework :: IPython',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
          'Programming Language :: FSharp',
          'Topic :: System :: Shells',
      ]
)
