
# F# and Fable (Python) support for Jupyter

Fable Python is an F# kernel for Jupyter based on [Fable](https://fable.io) and
[Metakernel](https://github.com/Calysto/metakernel). Fable is a transpiler that converts [F#](https://fsharp.org) to
Python (and JavaScript).

This work is work-in-progress and related to

- https://github.com/fable-compiler/Fable/issues/2339
- https://github.com/fable-compiler/Fable/pull/2345

## Install

```shell
pip3 install git+https://github.com/dbrattli/Fable.Jupyter.git
python3 -m fable_py install
```

If installing into the system, you may want to:

```shell
sudo pip3 install git+https://github.com/dbrattli/Fable.Jupyter.git
sudo python3 -m fable_py install
```

Or into your personal space:

```shell
pip3 install git+https://github.com/dbrattli/Fable.Jupyter.git --user
python3 -m fable_py install --user
```

Or into a virtualenv, when it is already activated:

```shell
pip3 install git+https://github.com/dbrattli/Fable.Jupyter.git.git
python3 -m fable_py install --sys-prefix
```

## Use

```shell
jupyter console --kernel fable-python
```

You can use Fable Python in the Jupyter notebook by selecting the "F# (Fable Python)" kernel.

```shell
jupyter lab
```

Note that a Fable compiler (w/Python support) also needs to be wathing in the background i.e:

```bash
>  dotnet fsi build.fsx jupyter
```
