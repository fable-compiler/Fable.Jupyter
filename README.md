
# Fable (Python)

Fable Python is an F# kernel for Jupyter based on [Metakernel](https://github.com/Calysto/metakernel). [Fable](https://fable.io) is a
transpiler that converts [F#](https://fsharp.org) to Python (and JavaScript)

## Install

```shell
pip3 install git+https://github.com/ekaschalk/jedhy.git
pip3 install git+https://github.com/Calysto/calysto_hy.git
python3 -m fable install
```

If installing into the system, you may want to:

```shell
sudo pip3 install git+https://github.com/dbrattli/Fable.Jupyter.git
sudo python3 -m fable install
```

Or into your personal space:

```shell
pip3 install git+https://github.com/dbrattli/Fable.Jupyter.git --user
python3 -m fable install --user
```

Or into a virtualenv, when it is already activated:

```shell
pip3 install git+https://github.com/dbrattli/Fable.Jupyter.git.git
python3 -m fable install --sys-prefix
```

## Use

```shell
jupyter console --kernel fable-python
```

You can use Fable Python in Jupyter notebook by selecting the "F# (Fable.py)" kernel.
