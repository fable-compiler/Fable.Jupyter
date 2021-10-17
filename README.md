
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

You can use Fable Python in the Jupyter notebook by selecting the "F# (Fable Python)" kernel.

```shell
dotnet run Jupyter
```
