
# F# and Fable (Python) support for Jupyter

Fable Python is an F# kernel for Jupyter based on [Fable](https://fable.io) and
[IPythonKernel](https://github.com/ipython/ipykernel). Fable is a transpiler that converts [F#](https://fsharp.org) to
Python (and JavaScript).

This work is work-in-progress and related to

- https://github.com/fable-compiler/Fable/issues/2339
- https://github.com/fable-compiler/Fable/pull/2345

## Install

```shell
pip install jupyter
pip install notebook
pip install git+https://github.com/dbrattli/Fable.Jupyter.git
python -m fable_py install
```

## Use

You can use Fable Python in the Jupyter notebook by selecting the "F# (Fable Python)" kernel.

```shell
jupyter notebook
```

Note that a Fable compiler (w/Python support) also needs to be watching in the background. Checkout Fable with branch
`beyond` in e.g folder `../Fable` relative to `Fable.Jupyter`. Then you can run Fable in another terminal like this:

```bash
> dotnet tool install fable-py
> dotnet fable-py watch src/fable.fsproj 2>> src/fable.out
```
