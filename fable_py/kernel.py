"""
An F# Fable (python) kernel for Jupyter based on MetaKernel.
"""
import io
import os
import re
import sys
import time
import traceback
import types

from metakernel import MetaKernel

from .version import __version__


def create_fallback_completer(env):
    """
    Return simple completions from env listing,
    macros and compile table
    """

    def complete(txt):
        matches = []
        return matches

    return complete


class Fable(MetaKernel):
    """
    A Jupyter kernel for F# based on MetaKernel.
    """

    implementation = "Fable"
    implementation_version = __version__
    language = "fs"
    language_version = "0.1"
    banner = "Fable is a compiler designed to make F# a first-class citizen of the Python ecosystem"
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
    # decl_regex = r"^(let)\s(\w*)|^(type)\s(\w*)\s*=|^(open)\s(\w*)\s"
    pyfile = "src/fable.py"
    fsfile = "src/Fable.fs"
    erfile = "src/fable.out"

    magic_prefixes = dict(magic="%", shell="!", help="?")
    help_suffix = None

    def __init__(self, *args, **kwargs):
        """
        Create the Fable (Python) environment
        """
        self.env = {}
        super(Fable, self).__init__(*args, **kwargs)

        # self.complete = create_completer(self.env)
        self.locals = {"__name__": "__console__", "__doc__": None}
        module_name = self.locals.get("__name__", "__console__")
        self.module = sys.modules.setdefault(module_name, types.ModuleType(module_name))
        self.module.__dict__.update(self.locals)
        self.locals = self.module.__dict__

        self.program = dict(module="module Fable.Jupyter")

    def set_variable(self, var, value):
        # print("set: ", var, value)
        self.env[var] = value

    def get_variable(self, var):
        return self.env[var]

    def do_execute_direct(self, code):
        """Execute the code, and return result."""
        # print("code: ", code)
        self.result = None

        # Handle some custom line magics. TODO: write a proper magic extension.
        if code == r"%pyfile":
            with open(self.pyfile, "r") as f:
                pycode = f.read()
                self.Print(pycode.strip())
                self.result = None
                return self.result
        elif code == r"%fsfile":
            with open(self.fsfile, "r") as f:
                fscode = f.read()
                self.Print(fscode.strip())
                self.result = None
                return self.result

        # try to parse it:
        try:
            with open(self.erfile, "r") as ef:
                ef.seek(0, io.SEEK_END)

                with open(self.fsfile, "w+"):  # Clear previous errors
                    pass
                mtime = os.path.getmtime(self.fsfile)

                expr = []
                decls = []

                # Update program declarations redefined in submitted code
                stmts = [stmt.lstrip("\n").rstrip() for stmt in re.split(self.stmt_regexp, code, re.M) if stmt]
                # print("Stmts: ", stmts)
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
                        self.result = ""
                        break

                    # Detect if the Python file have changed.
                    if os.path.getmtime(self.pyfile) > mtime:
                        with open(self.pyfile, "r") as f:
                            pycode = f.read()
                            exec_code = compile(pycode, self.pyfile, "exec")
                            self.result = eval(exec_code, self.locals)
                        break

                    time.sleep(0.1)
                else:
                    self.Error("Timeout! Are you sure Fable is running?")
                    self.result = ""

        except Exception as e:
            self.Error(traceback.format_exc())
            self.kernel_resp.update(
                {
                    "status": "error",
                    "ename": e.__class__.__name__,  # Exception name, as a string
                    "evalue": e.__class__.__name__,  # Exception value, as a string
                    "traceback": [],  # traceback frames as strings
                }
            )
            return None
        return self.result

    def get_completions(self, info):
        # txt = info["help_obj"]

        matches = []  # self.complete(txt)

        return matches
