"""
An F# Fable (python) kernel for Jupyter based on MetaKernel.
"""
import os
import re
import sys
import time
import traceback
import types
from collections import OrderedDict

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

    # For splitting code blocks into statements
    stmt_regexp = r"(?=^\w)"
    # For parsing a declaration (let, type, open) statement
    decl_regex = r"^(let)\s(\w*)|^(type)\s(\w*)\s*=|^(open)\s(\w*)\s"
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
        self.env[var] = value

    def get_variable(self, var):
        return self.env[var]

    def do_execute_direct(self, code):
        """Execute the code, and return result."""
        # print(sys.version)
        self.result = None
        # try to parse it:
        try:
            open(self.erfile, "w").close()  # Clear previous errors
            mtime = os.path.getmtime(self.erfile)

            expr = []
            decls = []

            # Remove program declarations redefined in submitted code
            stmts = [stmt for stmt in re.split(self.stmt_regexp, code) if stmt]
            for stmt in stmts:
                match = re.match(self.decl_regex, stmt)
                if match:
                    key = f"{match.group(1)} {match.group(2)}"
                    # print("program: ", self.program)
                    # print("key: ", key)
                    self.program.pop(key, None)
                    decls.append((key, stmt))

                # We need to print single expressions (except for those printing themselves)
                elif "printfn" not in stmt:
                    expr.append(stmt)

            program = [stmt for stmt in self.program.values()]

            # Print the result of a single expression.
            if len(expr) == 1 and not decls:
                code = f"""printfn "%A" ({code})"""

            # Write the F# file
            with open(self.fsfile, "w") as f:
                f.write(os.linesep.join(program))
                f.write(os.linesep)
                f.write(code)

            # Wait for Python file to be compiled
            for i in range(20):
                # Check for compile errors
                if os.path.getmtime(self.erfile) > mtime:
                    with open(self.erfile, "r") as f:
                        result = f.read()
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
                self.result = "timeout: %s : %s" % (mtime, os.path.getmtime(self.pyfile))

            # Update program
            for key, stmt in decls:
                self.program[key] = stmt

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
        txt = info["help_obj"]

        matches = self.complete(txt)

        return matches
