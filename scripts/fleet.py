#!/usr/bin/env python3
"""Operate the declared fleet using native services; never supervise runners.

Host-specific JSON lives outside the source checkout. One fleet manifest points
at host manifests on local/SSH hosts. Maintenance drains native GitHub routing,
stops execution, clears only declared cache paths and resumes previous services.
"""
import argparse
import datetime
import fcntl
import glob
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request


def run(args, *, capture=True, check=True, **kwargs):
    return subprocess.run(args, text=True, capture_output=capture, check=check, **kwargs)


def gh(endpoint, method="GET", body=None):
    args = ["gh", "api", endpoint, "--method", method]
    if body is not None:
        args += ["--input", "-"]
    result = run(args, input=json.dumps(body) if body is not None else None)
    return json.loads(result.stdout) if result.stdout.strip() else None


def owned(root, relative):
    """Reject symlink escapes and whole-root deletions before any mutation."""
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError(f"expected a path below the CI root: {relative}")
    path = root / relative
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents or path.is_symlink():
        raise ValueError(f"unsafe owned path: {relative}")
    return path


def service(config, action):
    if config["kind"] == "systemd":
        args = ["systemctl", "--user"]
        return run(args + [{"status": "is-active"}.get(action, action), config["unit"]], check=action != "status")
    target = f"gui/{os.getuid()}/{config['label']}"
    if action == "status":
        return run(["launchctl", "print", target], check=False)
    if action == "stop":
        state = run(["launchctl", "print", target]).stdout
        match = re.search(r"\bpid = (\d+)", state)
        result = run([config["bridge"], "unregister", config["agent"]]) if config["kind"] == "smappservice" else run(["launchctl", "bootout", target])
        if match:
            pid = int(match[1])
            deadline = time.monotonic() + 2400
            while True:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError(f"launchd process {pid} did not finish draining")
                time.sleep(1)
        return result
    if config["kind"] == "smappservice":
        return run([config["bridge"], "register", config["agent"]])
    return run(["launchctl", "bootstrap", f"gui/{os.getuid()}", config["plist"]])


def active(config):
    result = service(config, "status")
    if config["kind"] == "systemd":
        return result.stdout.strip() == "active"
    return result.returncode == 0 and "state = running" in result.stdout


def native_identity(root, native):
    metadata = json.loads((owned(root, native["directory"]) / ".runner").read_text(encoding="utf-8-sig"))
    if metadata["gitHubUrl"].rstrip("/") != "https://github.com/" + native["repository"]:
        raise ValueError(f"runner repository mismatch: {native['name']}")
    return f"repos/{native['repository']}/actions/runners/{metadata['agentId']}"


def host_status(config):
    root = Path(config["root"]).resolve(strict=True)
    result = {"root": str(root), "services": [], "native": [], "scale_sets": []}
    for entry in config.get("services", []) + [n["service"] for n in config.get("native", [])]:
        result["services"].append({"name": entry.get("unit", entry.get("label")), "active": active(entry)})
    for entry in config.get("native", []):
        endpoint = native_identity(root, entry)
        state = gh(endpoint)
        result["native"].append({"name": entry["name"], "status": state["status"], "busy": state["busy"]})
    if config.get("manager_config"):
        import tomllib
        manager = tomllib.loads(owned(root, config["manager_config"]).read_text())
        result["concurrent"] = manager["concurrent"]
        for entry in manager["scaleset"]:
            result["scale_sets"].append({k: entry[k] for k in ("name", "max-runners")})
    last = root / "maintenance.json"
    result["maintenance"] = json.loads(last.read_text()) if last.exists() else None
    result["free_bytes"] = shutil.disk_usage(root).free
    if config.get("health_url"):
        with urllib.request.urlopen(config["health_url"], timeout=10) as response:
            result["health"] = json.load(response)
    result["ok"] = all(s["active"] for s in result["services"]) and all(n["status"] == "online" for n in result["native"])
    return result


def install_native(config, config_path):
    root = Path(config["root"]).resolve(strict=True)
    for native in config.get("native", []):
        owned(root, native["directory"]).resolve(strict=True)
        svc = native["service"]
        args = [sys.executable, str(Path(__file__).resolve()), str(config_path), "run-native", native["name"]]
        logs = root / "logs" / native["name"]
        logs.mkdir(parents=True, exist_ok=True)
        if svc["kind"] == "smappservice":
            # macOS attribution must belong to the signed owning application.
            # Never install a Python/shell Program in ~/Library/LaunchAgents.
            service(svc, "start")
            print(json.dumps({"registered": svc["label"], "owner": "GitHub Actions Runner.app"}), flush=True)
            continue
        if svc["kind"] == "systemd":
            if not svc["unit"].startswith("github-actions-runner-native-"):
                raise ValueError("native units must use the project prefix")
            path = Path.home() / ".config/systemd/user" / svc["unit"]
            # systemd quoting differs from a shell: escape its % specifiers too.
            quote = lambda value: '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'
            path.write_text("[Unit]\nDescription=GitHub Actions Runner - " + native["name"] + "\nAfter=network-online.target\n\n[Service]\nExecStart=" + " ".join(map(quote, args)) + "\nRestart=always\nRestartSec=10\nKillSignal=SIGINT\nTimeoutStopSec=120\n\n[Install]\nWantedBy=default.target\n")
            run(["systemctl", "--user", "daemon-reload"])
            run(["systemctl", "--user", "enable", svc["unit"]])
        else:
            raise ValueError("macOS native runners require the signed app's SMAppService")
        print(json.dumps({"installed": str(path)}), flush=True)


def run_native(config, name):
    root = Path(config["root"]).resolve(strict=True)
    native = next(n for n in config["native"] if n["name"] == name)
    os.chdir(owned(root, native["directory"]))
    env = os.environ | native.get("environment", {})
    os.execvpe(native["command"][0], native["command"], env)


def cache_paths(config, root):
    paths = []
    for pattern in config.get("cache_paths", []):
        owned(root, pattern)  # validate before expanding even an unmatched pattern
        for match in glob.glob(str(root / pattern)):
            path = owned(root, str(Path(match).relative_to(root)))
            if path.is_dir():
                paths.append(path)
    unique = set(paths)
    return sorted(p for p in unique if not any(parent in unique for parent in p.parents))


def clear_caches(config, root):
    paths = cache_paths(config, root)
    if paths and config.get("cleanup_image"):
        # Root inside a networkless container handles uid-1001 shared caches.
        # No daemon-wide image, build-cache, container or volume pruning.
        targets = ["/fleet/" + str(p.relative_to(root)) for p in paths]
        run(["docker", "run", "--rm", "--network", "none", "--user", "0",
             "--mount", f"type=bind,source={root},target=/fleet", "--entrypoint", "/usr/bin/find",
             config["cleanup_image"], *targets, "-mindepth", "1", "-delete"])
    else:
        for path in paths:
            for child in path.iterdir():
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
    # Logs are separate from caches; private evidence is never an implicit cache.
    before = time.time() - config.get("log_days", 14) * 86400
    for pattern in config.get("log_paths", []):
        owned(root, pattern)
        for match in glob.glob(str(root / pattern)):
            path = owned(root, str(Path(match).relative_to(root)))
            if path.is_file() and path.stat().st_mtime < before:
                path.unlink()
            elif path.is_file() and path.stat().st_size > config.get("max_log_bytes", 10 * 1024 * 1024):
                with path.open("rb+") as output:
                    output.seek(-config.get("max_log_bytes", 10 * 1024 * 1024), 2)
                    tail = output.read()
                    output.seek(0)
                    output.write(tail)
                    output.truncate()
    return [str(p.relative_to(root)) for p in paths]


def prune_owned_images(config):
    removed = []
    for policy in config.get("image_retention", []):
        prefix = policy["repository_prefix"]
        if not prefix or prefix == "*":
            raise ValueError("image retention requires an explicit repository prefix")
        images = run(["docker", "image", "ls", "--format", "{{json .}}"]).stdout.splitlines()
        before = time.time() - policy["days"] * 86400
        for line in images:
            entry = json.loads(line)
            if not entry["Repository"].startswith(prefix) or entry["Tag"] == "<none>":
                continue
            reference = entry["Repository"] + ":" + entry["Tag"]
            created = run(["docker", "image", "inspect", reference, "--format", "{{.Created}}"]).stdout.strip()
            if datetime.datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp() < before:
                # Remove only this owned tag. Never force-remove running images
                # or remove unrelated tags sharing the same image ID.
                run(["docker", "image", "rm", reference])
                removed.append(reference)
    return removed


def wait_manager_idle(config, root):
    if not config.get("manager_config"):
        return
    import tomllib
    manager = tomllib.loads(owned(root, config["manager_config"]).read_text())
    repositories = sorted({s["url"].removeprefix("https://github.com/").rstrip("/") for s in manager["scaleset"]})
    deadline = time.monotonic() + config.get("drain_seconds", 5400)
    quiet_since = None
    while True:
        # GitHub knows a job has been assigned before the scale-set listener
        # receives JobStarted. Do not rely on the manager's busy=0 alone: its
        # idle-runner drain can otherwise remove an already assigned worker.
        busy = False
        for repository in repositories:
            response = gh(f"repos/{repository}/actions/runs?status=in_progress&per_page=100")
            busy |= bool(response["workflow_runs"])
        now = time.monotonic()
        if busy:
            quiet_since = None
        else:
            if quiet_since is None:
                quiet_since = now
            if now - quiet_since >= config.get("quiet_seconds", 15):
                return
        if now > deadline:
            raise TimeoutError("GitHub workflows stayed active; caches were not cleared")
        time.sleep(5)


def maintain_host(config):
    root = Path(config["root"]).resolve(strict=True)
    result = {"started": time.time(), "ok": False}
    restored_labels = []
    restart = []
    with (root / "maintenance.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            # Remove the routing labels first, so existing jobs can finish and
            # current workflows cannot dispatch new work during cache reset.
            for native in config.get("native", []):
                endpoint = native_identity(root, native)
                labels = [x["name"] for x in gh(endpoint + "/labels")["labels"] if x["type"] == "custom"]
                if not labels:
                    raise ValueError(f"native runner has no custom routing label: {native['name']}")
                restored_labels.append((endpoint, labels))
                gh(endpoint + "/labels", "DELETE")
            deadline = time.monotonic() + config.get("drain_seconds", 5400)
            for endpoint, _ in restored_labels:
                while gh(endpoint)["busy"]:
                    if time.monotonic() > deadline:
                        raise TimeoutError("native job did not finish before maintenance deadline")
                    time.sleep(5)
            wait_manager_idle(config, root)
            execution = [s for s in config.get("services", []) if s.get("execution")] + [n["service"] for n in config.get("native", [])]
            for svc in execution:
                if active(svc):
                    restart.append(svc)
                    service(svc, "stop")
            # launchctl bootout returns before its process has necessarily exited.
            for native in config.get("native", []):
                directory = str(owned(root, native["directory"]))
                while True:
                    processes = run(["ps", "-axo", "comm"]).stdout.splitlines()
                    if not any(p.strip().startswith(directory + "/") and "Runner." in p for p in processes):
                        break
                    if time.monotonic() > deadline:
                        raise TimeoutError("native runner process did not stop")
                    time.sleep(1)
            result["cleared"] = clear_caches(config, root)
            for command in config.get("cache_commands", []):
                run(command, env=os.environ | config.get("cache_environment", {}))
            result["removed_images"] = prune_owned_images(config)
            result["ok"] = True
        except Exception as error:
            result["error"] = str(error)
        finally:
            for svc in reversed(restart):
                try:
                    service(svc, "start")
                except Exception as error:
                    result.update(ok=False, restart_error=str(error))
            for endpoint, labels in restored_labels:
                try:
                    gh(endpoint + "/labels", "POST", {"labels": labels})
                except Exception as error:
                    result.update(ok=False, labels_error=str(error))
            result["finished"] = time.time()
            (root / "maintenance.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("action", choices=["status", "maintain", "install-native", "run-native"])
    parser.add_argument("name", nargs="?")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if "hosts" in config:
        if args.action not in ("status", "maintain"):
            parser.error("fleet manifests support status and maintain")
        failed = False
        for host in config["hosts"]:
            command = [host.get("python", "python3"), host["script"], host["config"], args.action]
            if host.get("ssh"):
                command = ["ssh", "-o", "BatchMode=yes", host["ssh"], shlex.join(command)]
            output = run(command, check=False)
            try:
                contents = json.loads(output.stdout)
            except ValueError:
                contents = output.stdout.strip()
            print(json.dumps({"host": host["name"], "exit_code": output.returncode,
                              "result": contents, "error": output.stderr.strip()}), flush=True)
            failed |= output.returncode != 0
        return int(failed)
    if args.action == "install-native":
        install_native(config, args.config.resolve())
    elif args.action == "run-native":
        run_native(config, args.name)
    else:
        result = host_status(config) if args.action == "status" else maintain_host(config)
        print(json.dumps(result, indent=2), flush=True)
        return 0 if result.get("ok", True) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
