"""
An F# Fable (python) kernel for Jupyter based on IPythonKernel.
"""
import io
import json
import os
import pkgutil
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import traceback

from jupyter_core.paths import jupyter_config_path, jupyter_config_dir
from ipykernel.ipkernel import IPythonKernel
from ipykernel.kernelapp import IPKernelApp
from traitlets.config import Application

from .version import __version__


def format_message(*objects, **kwargs):
    """
    Format a message like print() does.
    """
    objects = [str(i) for i in objects]
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    return sep.join(objects) + end


try:
    from IPython.utils.PyColorize import NeutralColors

    RED = NeutralColors.colors["header"]
    NORMAL = NeutralColors.colors["normal"]
except Exception:
    from IPython.core.excolors import TermColors

    RED = TermColors.Red
    NORMAL = TermColors.Normal


class Fable(IPythonKernel):
    """
    A Jupyter kernel for F# based on IPythonKernel.
    """

    app_name = "Fable Python"
    implementation = "Fable Python"
    implementation_version = __version__
    language = "fs"
    language_version = "0.2"
    banner = "Fable Python is a compiler designed to make F# a first-class citizen of the Python ecosystem."
    language_info = {
        "name": "fsharp",
        "mimetype": "text/x-fsharp",
        "pygments_lexer": "fsharp",
        "file_extension": ".fs",
    }

    kernel_json = {
        "argv": [sys.executable, "-m", "fable_py", "-f", "{connection_file}"],
        "display_name": "F# (Fable Python)",
        "language": "fsharp",
        "codemirror_mode": "fsharp",
        "name": "fable-python",
    }

    # For splitting code blocks into statements (lines that start with identifiers or [)
    stmt_regexp = r"\n(?=[\w\[])"
    # For parsing a declaration (let, type, open) statement
    decl_regex = (
        r"^(let)\s+(?P<let>\w+)"  # e.g: let a = 10
        r"|^(let)\s+``(?P<ticked>[\w ]+)``"  # e.g: let ``end`` = "near"
        r"|^(type)\s+(?P<type>\w*)[\s\(]"  # e.g: type Test () class end
        r"|^(open)\s+(?P<open>[\w.]+)"  # e.g: open Fable.Core
        r"|^\[<(?P<attr>.*)>\]"  # e.g: [<Import(..)>]
    )
    pyfile = "src/fable.py"
    fsfile = "src/Fable.fs"
    erfile = "src/fable.out"

    magic_prefixes = dict(magic="%", shell="!", help="?")
    help_suffix = None

    def __init__(self, *args, **kwargs):
        """
        Create the Fable (Python) environment
        """
        super(Fable, self).__init__(*args, **kwargs)

        self.program = dict(module="module Fable.Jupyter")
        self.env = {}

        sys.path.append("src")

    def Print(self, *objects, **kwargs):
        """Print `objects` to the iopub stream, separated by `sep` and
        followed by `end`. Items can be strings or `Widget` instances.
        """
        message = format_message(*objects, **kwargs)

        stream_content = {"name": "stdout", "text": message}
        self.log.debug("Print: %s" % message.rstrip())
        self.send_response(self.iopub_socket, "stream", stream_content)

    def Error(self, *objects, **kwargs):
        """Print `objects` to stdout, separated by `sep` and followed by
        `end`. Objects are cast to strings.
        """
        message = format_message(*objects, **kwargs)
        self.log.debug("Error: %s" % message.rstrip())
        stream_content = {"name": "stderr", "text": RED + message + NORMAL}
        self.send_response(self.iopub_socket, "stream", stream_content)

    def restart_kernel(self):
        self.Print("Restarting kernel...")

        # Clear F# file
        open(self.fsfile, "w").close()
        self.Print("Done!")

    def do_shutdown(self, restart):
        if restart:
            self.restart_kernel()

        return super().do_shutdown(restart)

    def set_variable(self, var, value):
        # print("set: ", var, value)
        self.env[var] = value

    def get_variable(self, var):
        return self.env[var]

    def ok(self):
        return {
            "status": "ok",
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }

    async def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        """Execute the code, and return result."""
        # print("code: ", code)

        # Handle some custom line magics. TODO: write a proper magic extension.
        if code == r"%python":
            with open(self.pyfile, "r") as f:
                pycode = f.read()
                self.Print(pycode.strip())
                return self.ok()
        elif code == r"%fsharp  ":
            with open(self.fsfile, "r") as f:
                fscode = f.read()
                self.Print(fscode.strip())
                return self.ok()
        elif code.startswith(r"%%python"):
            code = code.replace(r"%%python", "")
            return await super().do_execute(code, silent, store_history, user_expressions, allow_stdin)

        lines = code.splitlines()
        code = "\n".join([line for line in lines if not line.startswith("%")])
        magics = "\n".join([line for line in lines if line.startswith("%")])

        try:
            with open(self.erfile, "r") as ef:
                ef.seek(0, io.SEEK_END)

                open(self.fsfile, "w+").close()  # Clear previous errors

                mtime = os.path.getmtime(self.fsfile)

                expr = []
                decls = []

                # Update program declarations redefined in submitted code
                stmts = [stmt.lstrip("\n").rstrip() for stmt in re.split(self.stmt_regexp, code, re.M) if stmt]
                for stmt in stmts:
                    match = re.match(self.decl_regex, stmt)
                    if match:
                        matches = dict((key, value) for (key, value) in match.groupdict().items() if value)
                        key = f"{list(matches.keys())[0]} {list(matches.values())[0]}"
                        # print("program: ", self.program)
                        # print("key: ", key)
                        self.program[key] = stmt
                        decls.append((key, stmt))

                    # We need to print single expressions (except for those printing themselves)
                    else:
                        expr.append(stmt)

                # Construct the F# program (current and past declarations)
                program = [stmt for stmt in self.program.values()]

                # Print the result of a single expression. # TODO: can we simplify?
                if len(expr) == 1 and "printf" not in expr[0] and not decls:
                    expr = [f"""printfn "%A" ({expr[0]})"""]

                # Write the F# program to file
                with open(self.fsfile, "w") as f:
                    f.write("\n".join(program))
                    f.write("\n")
                    f.write("\n".join(expr))

                # Wait for Python file to be compiled
                for i in range(20):
                    # Check for compile errors
                    if os.path.getmtime(self.erfile) > mtime:
                        result = ef.read()
                        self.Error(result)
                        return self.ok()

                    # Detect if the Python file have changed.
                    if os.path.getmtime(self.pyfile) > mtime:
                        with open(self.pyfile, "r") as f:
                            pycode = f.read()
                            pycode = magics + "\n" + pycode
                            return await super().do_execute(
                                pycode, silent, store_history, user_expressions, allow_stdin
                            )
                    elif magics:
                        return await super().do_execute(magics, silent, store_history, user_expressions, allow_stdin)
                    time.sleep(0.1)
                else:
                    self.Error("Timeout! Are you sure Fable is running?")
                    return self.ok()

        except Exception as e:
            self.Error(traceback.format_exc())
            return {
                "status": "error",
                "ename": e.__class__.__name__,  # Exception name, as a string
                "evalue": e.__class__.__name__,  # Exception value, as a string
                "traceback": [],  # traceback frames as strings
            }

        return self.ok()

    def get_completions(self, info):
        # txt = info["help_obj"]

        return []

    @classmethod
    def run_as_main(cls, *args, **kwargs):
        """Launch or install the kernel."""

        kwargs["app_name"] = cls.app_name
        FableKernelApp.launch_instance(kernel_class=cls, *args, **kwargs)


# Borrwed from Metakernel, https://github.com/Calysto/metakernel
class FableKernelApp(IPKernelApp):
    """The FableKernel launcher application."""

    config_dir = str()

    def _config_dir_default(self):
        return jupyter_config_dir()

    @property
    def config_file_paths(self):
        path = jupyter_config_path()
        if self.config_dir not in path:
            path.insert(0, self.config_dir)
        path.insert(0, os.getcwd())
        return path

    @classmethod
    def launch_instance(cls, *args, **kwargs):
        cls.name = kwargs.pop("app_name", "metakernel")
        super(FableKernelApp, cls).launch_instance(*args, **kwargs)

    @property
    def subcommands(self):
        # Slightly awkward way to pass the actual kernel class to the install
        # subcommand.

        class KernelInstallerApp(Application):
            kernel_class = self.kernel_class

            def initialize(self, argv=None):
                self.argv = argv

            def start(self):
                kernel_spec = self.kernel_class().kernel_json
                with TemporaryDirectory() as td:
                    dirname = os.path.join(td, kernel_spec["name"])
                    os.mkdir(dirname)
                    with open(os.path.join(dirname, "kernel.json"), "w") as f:
                        json.dump(kernel_spec, f, sort_keys=True)
                    filenames = ["logo-64x64.png", "logo-32x32.png"]
                    name = self.kernel_class.__module__
                    for filename in filenames:
                        try:
                            data = pkgutil.get_data(name.split(".")[0], "images/" + filename)
                        except (OSError, IOError):
                            data = pkgutil.get_data("metakernel", "images/" + filename)
                        with open(os.path.join(dirname, filename), "wb") as f:
                            f.write(data) if data else None
                    try:
                        subprocess.check_call(
                            [sys.executable, "-m", "jupyter", "kernelspec", "install"] + self.argv + [dirname]
                        )
                    except subprocess.CalledProcessError as exc:
                        sys.exit(exc.returncode)

        return {"install": (KernelInstallerApp, "Install this kernel")}
