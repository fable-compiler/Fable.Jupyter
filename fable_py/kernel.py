"""
An F# Fable (python) kernel for Jupyter based on IPythonKernel.
"""
import io
import json
import os
import os.path
import pkgutil
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
from tempfile import TemporaryDirectory

try:
    import black
except ImportError:
    black = None

from ipykernel.ipkernel import IPythonKernel
from ipykernel.kernelapp import IPKernelApp
from IPython.display import Code
from jupyter_core.paths import jupyter_config_dir, jupyter_config_path
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

    fsproj = """<?xml version="1.0" encoding="utf-8"?>
<Project Sdk="Microsoft.NET.Sdk">
<PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net5</TargetFramework>
    <RollForward>Major</RollForward>
    <LangVersion>preview</LangVersion>
    <DisableImplicitFSharpCoreReference>true</DisableImplicitFSharpCoreReference>
</PropertyGroup>
<ItemGroup>
    <Compile Include="Fable.fs" />
</ItemGroup>
<ItemGroup>
    <PackageReference Include="FSharp.Core" Version="6.0.1" />
    <PackageReference Include="Fable.Core.Experimental" Version="4.0.0-alpha-010" />
    <PackageReference Include="Fable.Python" Version="0.16.0" />
</ItemGroup>
</Project>
"""

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

    magic_prefixes = dict(magic="%", shell="!", help="?")
    help_suffix = None

    def __init__(self, *args, **kwargs):
        """
        Create the Fable (Python) environment
        """
        super(Fable, self).__init__(*args, **kwargs)

        self.program = dict(module="module Fable.Jupyter")
        self.env = {}

        self.tmp_dir = TemporaryDirectory()
        self.pyfile = os.path.join(self.tmp_dir.name, "fable.py")
        self.fsfile = os.path.join(self.tmp_dir.name, "Fable.fs")

        self.fable = None
        self.start_fable()

    def start_fable(self):
        self.log.info("Starting Fable ...")
        sys.path.append(self.tmp_dir.name)
        with open(os.path.join(self.tmp_dir.name, "Jupyter.fsproj"), "w") as fd:
            fd.write(self.fsproj)
            fd.flush()

        self.fable = subprocess.Popen(
            ["dotnet", "fable-py", self.tmp_dir.name, "--watch"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        def error_reader(proc, outq):
            for line in iter(proc.stderr.readline, b""):
                outq.put(line.decode("utf-8"))

        self.errors = queue.Queue()
        self.error_thread = threading.Thread(target=error_reader, args=(self.fable, self.errors))
        self.error_thread.start()

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

    def Code(self, code: Code):
        """Print HTML formatted code to stdout."""
        content = {"data": {"text/html": code._repr_html_(), "text/plain": repr(code)}, "metadata": {}}
        self.send_response(self.iopub_socket, "display_data", content)

    def restart_kernel(self):
        self.Print("Restarting kernel...")

        # Clear F# file
        open(self.fsfile, "w").close()
        self.Print("Done!")

    def do_shutdown(self, restart):
        if restart:
            self.restart_kernel()

        else:
            self.tmp_dir.cleanup()
            if self.fable:
                self.fable.terminate()

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

    async def do_magic(self, code: str, silent, store_history=True, user_expressions=None, allow_stdin=False):
        # Handle some custom line magics.
        if code == r"%python":
            with open(self.pyfile, "r") as f:
                pycode = f.read()
                if black:
                    pycode = black.format_str(pycode, mode=black.FileMode())
                code_ = Code(pycode.strip(), language="python")
                self.Code(code_)
                return self.ok()
        elif code == r"%fsharp":
            with open(self.fsfile, "r") as f:
                fscode = f.read()
                code_ = Code(fscode.strip(), language="fsharp")
                self.Code(code_)
                return self.ok()

        # Reset command
        elif code.startswith(r"%reset"):
            self.restart_kernel()
            return await super().do_execute(code, silent, store_history, user_expressions, allow_stdin)

        # Send all cell magics straight to the IPythonKernel
        elif code.startswith(r"%%"):
            # Make sure Python runs in the same context as us
            code = code.replace(r"%%python", "")
            return await super().do_execute(code, silent, store_history, user_expressions, allow_stdin)

        return

    async def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        """Execute the code, and return result."""

        ret = await self.do_magic(code, silent, store_history, user_expressions, allow_stdin)
        if ret:
            return ret

        program = self.program.copy()
        lines = code.splitlines()
        code = "\n".join([line for line in lines if not line.startswith("%")])
        magics = "\n".join([line for line in lines if line.startswith("%")])

        try:
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
                    program[key] = stmt
                    decls.append((key, stmt))

                # We need to print single expressions (except for those printing themselves)
                else:
                    expr.append(stmt)

            # Print the result of a single expression.
            if len(expr) == 1 and "printf" not in expr[0] and not decls:
                expr = [f"""printfn "%A" ({expr[0]})"""]
            elif not expr:
                # Add an empty do-expression to make sure the program compiles
                expr = ["do ()"]

            # Construct the F# program (current and past declarations) and write the program to file.
            with open(self.fsfile, "w") as f:
                f.write("\n".join(program.values()))
                f.write("\n")
                f.write("\n".join(expr))

            # Wait for Python file to be compiled
            for i in range(60):
                # Check for compile errors

                # Detect if the Python file have changed since last compile.
                if os.path.exists(self.pyfile) and os.path.getmtime(self.pyfile) > mtime:
                    with open(self.pyfile, "r") as f:
                        pycode = f.read()
                        pycode = magics + "\n" + pycode

                        # Only update program if compiled successfully so we don't get stuck with a failing program
                        self.program = program
                        return await super().do_execute(pycode, silent, store_history, user_expressions, allow_stdin)
                elif magics:
                    return await super().do_execute(magics, silent, store_history, user_expressions, allow_stdin)
                elif not self.errors.empty():
                    size = self.errors.qsize()
                    lines = [self.errors.get(block=False) for _ in range(size)]
                    self.Error("\n".join(lines))
                    return self.ok()
                time.sleep(i / 10.0)
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


# Borrowed from Metakernel, https://github.com/Calysto/metakernel
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
                kernel_spec = self.kernel_class.kernel_json
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
