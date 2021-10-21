
# F# and Fable (Python) support for Jupyter

Fable Python is an F# kernel for Jupyter based on [Fable](https://fable.io) and
[IPythonKernel](https://github.com/ipython/ipykernel). Fable is a transpiler that converts [F#](https://fsharp.org) to
Python (and JavaScript).

This work is work-in-progress and related to

- https://github.com/fable-compiler/Fable/issues/2339
- https://github.com/fable-compiler/Fable/pull/2345

## Install

```shell
git clone https://github.com/dbrattli/Fable.Jupyter.git
cd Fable.Jupyter

dotnet tool restore
dotnet restore
dotnet run InstallKernel
```

## Usage

You can use Fable Python in the Jupyter notebook by selecting the "F#
(Fable Python)" kernel. To start the kernel run:

```shell
dotnet run Jupyter
```

The process currently needs to be running while using the notebook.
TODO: see if we can do it the other way around and start dotnet from
Python instead.

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
scenes. This program lives in the `src` folder.

Sometimes the generated F# program might become invalid because of the
submitted code fragments (this happens with a Python notebook as well).
The way to recover is to reset the kernel. That will reset the F#
program that is running behind the notebook. To reset the kernel select
on the menu: `Kernel -> Restart` or `Kernel -> Restart & Clear Output`.

If you need additional package references you currently need to add them
manually to the `Fable.fsproj` project file. TODO: handle `#r nuget
"...` commands from within the notebook.