import subprocess
import sys


def run_step(module_name: str) -> None:
    print(f"[BOOTSTRAP] Running: python -m {module_name}")
    result = subprocess.run([sys.executable, "-m", module_name], check=False)
    if result.returncode != 0:
        raise SystemExit(f"[BOOTSTRAP] Failed step: {module_name}")


def main() -> None:
    run_step("scripts.ingest_sources")
    run_step("scripts.build_index")
    print("[BOOTSTRAP] RAG initialization completed.")


if __name__ == "__main__":
    main()
