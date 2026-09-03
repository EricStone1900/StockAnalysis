"""Sandbox Adapter：只构造安全的固定脚本执行命令。"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256

from .domain import ExperimentInput

ALLOWED_SCRIPT_IDS = frozenset({"fixed-factor-smoke-v1"})


@dataclass(frozen=True)
class SandboxCommand:
    argv: tuple[str, ...]
    config_hash: str


@dataclass(frozen=True)
class SandboxExecution:
    exit_code: int | None
    metrics: dict[str, float]
    rejected_reason: str | None = None


SandboxExecutor = Callable[[SandboxCommand, int, int], SandboxExecution]


class FixedScriptSandbox:
    """构造无网络、最小权限的Docker Sandbox命令，不执行任意用户代码。"""

    def build_command(self, input_value: ExperimentInput) -> SandboxCommand:
        if input_value.script_id not in ALLOWED_SCRIPT_IDS:
            raise ValueError("script_id is not allow-listed")
        budget = input_value.budget
        args = (
            "docker", "run", "--rm", "--network", "none", "--read-only", "--user", "65532:65532",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", str(budget.pid_limit),
            "--cpus", str(budget.cpu_limit), "--memory", f"{budget.memory_mb}m", "--tmpfs", f"/tmp:rw,noexec,nosuid,size={budget.disk_mb}m",
            "--mount", f"type=bind,src=/artifacts/{input_value.data_artifact_hash},dst=/input,readonly",
            "--workdir", "/tmp", "research-sandbox:fixed-v1", input_value.script_id,
        )
        config = {"argv": args, "dataVersionId": input_value.data_version_id, "inputHash": input_value.content_hash}
        return SandboxCommand(args, sha256(json.dumps(config, separators=(",", ":")).encode()).hexdigest())

    def execute(self, input_value: ExperimentInput, executor: SandboxExecutor | None = None) -> SandboxExecution:
        command = self.build_command(input_value)
        return (executor or _subprocess_executor)(command, input_value.budget.timeout_seconds, input_value.budget.log_limit_bytes)


def _subprocess_executor(command: SandboxCommand, timeout_seconds: int, log_limit_bytes: int) -> SandboxExecution:
    try:
        completed = subprocess.run(command.argv, check=False, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return SandboxExecution(None, {}, "sandbox timeout")
    output_size = len(completed.stdout.encode()) + len(completed.stderr.encode())
    if output_size > log_limit_bytes:
        return SandboxExecution(completed.returncode, {}, "sandbox log limit exceeded")
    if completed.returncode != 0:
        return SandboxExecution(completed.returncode, {}, "sandbox exited unsuccessfully")
    return SandboxExecution(0, {})
