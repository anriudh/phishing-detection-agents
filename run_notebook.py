"""Run phishing_detection.ipynb without a browser, in the local venv, and print what each cell outputs.

The venv lives outside OneDrive (so OneDrive doesn't sync thousands of package files),
at %USERPROFILE%\\.venvs\\phishing. Usage, from the project folder:
    ~/.venvs/phishing/Scripts/python run_notebook.py                         # run every cell
    ~/.venvs/phishing/Scripts/python run_notebook.py --until "Checkpoint 2"  # stop after the first code cell containing this text

The executed copy, with outputs, is saved to runtime/executed.ipynb (git-ignored).
The notebook in git stays output-free.
"""
import argparse, os, re, sys
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

HERE = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.path.join(HERE, "phishing_detection.ipynb")
EXECUTED = os.path.join(HERE, "runtime", "executed.ipynb")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def secret_values():
    """The API key, so it can be blanked out if it ever shows up in an output."""
    values = [os.environ.get("GEMINI_API_KEY", "")]
    env_file = os.path.join(HERE, ".env")
    if os.path.exists(env_file):
        for line in open(env_file, encoding="utf-8"):
            name, _, value = line.strip().partition("=")
            if name.strip() == "GEMINI_API_KEY":
                values.append(value.strip().strip('"'))
    return [v for v in values if len(v) > 8]


def output_text(output):
    if output.output_type == "stream":
        return output.text
    if output.output_type in ("execute_result", "display_data"):
        return output.get("data", {}).get("text/plain", "")
    if output.output_type == "error":
        return ANSI.sub("", "\n".join(output.traceback))
    return ""


def main():
    sys.stdout.reconfigure(encoding="utf-8")   # the Windows console default can't print ✅
    parser = argparse.ArgumentParser()
    parser.add_argument("--until", help="stop after the first code cell whose source contains this text")
    parser.add_argument("--smoke-test", action="store_true",
                        help="also run the Stage 1 smoke test (about 3 API requests); skipped by default")
    parser.add_argument("--model", help="use this Gemini model instead of the config's PRIMARY_MODEL (development only)")
    args = parser.parse_args()
    # The kernel inherits these environment variables; the notebook's config cell reads them.
    os.environ["RUN_SMOKE_TEST"] = "1" if args.smoke_test else "0"
    if args.model:
        os.environ["PHISH_MODEL"] = args.model

    nb = nbformat.read(NOTEBOOK, as_version=4)
    if args.until:
        stop = next((i for i, c in enumerate(nb.cells)
                     if c.cell_type == "code" and args.until in c.source), None)
        if stop is None:
            sys.exit(f"No code cell contains {args.until!r}")
        nb.cells = nb.cells[:stop + 1]

    client = NotebookClient(nb, timeout=None, kernel_name="python3",
                            resources={"metadata": {"path": HERE}})
    failed = None
    try:
        client.execute()
    except CellExecutionError as e:
        failed = e

    secrets = secret_values()
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code" or cell.get("execution_count") is None:
            continue
        print(f"\n===== cell {i}: {cell.source.splitlines()[0][:80] if cell.source else ''}")
        for output in cell.outputs:
            text = output_text(output)
            for s in secrets:
                text = text.replace(s, "[REDACTED]")
            # Store the cleaned text back, so the saved copy can't contain the key either
            if output.output_type == "stream":
                output.text = text
            elif output.output_type == "error":
                output.traceback = text.split("\n")
            elif "text/plain" in output.get("data", {}):
                output.data = {"text/plain": text}
            print(text.rstrip())

    os.makedirs(os.path.dirname(EXECUTED), exist_ok=True)
    nbformat.write(nb, EXECUTED)
    print("\nexecuted copy:", EXECUTED)
    if failed:
        sys.exit("A cell raised an error (see its traceback above).")


if __name__ == "__main__":
    main()
