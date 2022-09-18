# F# and Fable (Python) support for Jupyter

Fable Python is an F# kernel for Jupyter based on [Fable](https://fable.io) and
[IPythonKernel](https://github.com/ipython/ipykernel). Fable is a transpiler
that converts [F#](https://fsharp.org) to Python (and JavaScript).

This work is work-in-progress and related to

- https://github.com/fable-compiler/Fable/issues/2339
- https://github.com/fable-compiler/Fable/pull/2345

## Install

Make sure you have a recent version of .NET installed on your machine:
https://dotnet.microsoft.com/download

You also need to install the latest `fable-py` .NET tool globally (and
make sure it's available in PATH environment)

```sh
dotnet tool install -g fable --prerelease

pip install fable-py
python -m fable_py install
```

To use the very latest changes (for development):

```sh
git clone https://github.com/dbrattli/Fable.Jupyter.git
cd Fable.Jupyter
python setup.py develop
python -m fable_py install
```

## Usage

You can use Fable Python in the Jupyter notebook by selecting the "F#
(Fable Python)" kernel. To start Jupyter run e.g:

```shell
jupyter notebook

# or

jupyter lab
```

## Magic commands

You can inspect the generated Python code by executing `%python` in a cell:

```
%python
```

You can inspect the maintained F# program by executing `%fsharp` in a cell:

```
%fsharp
```

## F# Program

The kernel works by maintaining an F# program `Fable.fs` behind the
scenes. This program lives in a separate `tmp` folder for each instance
of the kernel.

Sometimes the generated F# program might become invalid because of the
submitted code fragments (this can happen with a Python notebook as well).
The way to recover is to reset the kernel. That will reset the F#
program that is running behind the notebook. To reset the kernel select
on the menu: `Kernel -> Restart` or `Kernel -> Restart & Clear Output`.

or you can use the reset command:

```
%reset
```

If you need additional package references you currently need to add them
manually to the `Fable.fsproj` project file. TODO: handle `#r nuget "...` commands from within the notebook.
