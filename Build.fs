open System.IO

open Fake.Core
open Fake.IO

open Helpers

initializeContext()

let kernelPath = Path.getFullName "fable_py"
let srcPath = Path.getFullName "src"

Target.create "InstallKernel" (fun _ ->
    run pip "install jupyter notebook" "."
    run python "-m fable_py install" "."
    run pip "install ." "."
)

Target.create "Clean" (fun _ ->
    run dotnet "fable-py clean --yes" srcPath // Delete *.fs.js files created by Fable
)

Target.create "Jupyter" (fun _ ->
    do Environment.setEnvironVar "FABLE_JUPYTER_DIR" (Directory.GetCurrentDirectory ())
    [ "jupyter", jupyter "notebook" "."
      "fable", dotnetRedirect "fable-py watch fable.fsproj" "src" "src/fable.out" ]
    |> runParallel
)

Target.create "Jupyter-Lab" (fun _ ->
    [ "jupyter", jupyter "lab" "."
      "fable", dotnetRedirect "fable-py watch fable.fsproj" "src" "src/fable.out" ]
    |> runParallel
)

open Fake.Core.TargetOperators

let dependencies = [
    "Clean"
        ==> "InstallKernel"
    "Clean"
        ==> "Jupyter"
    "Clean"
        ==> "Jupyter-Lab"
]

[<EntryPoint>]
let main args = runOrDefault args
