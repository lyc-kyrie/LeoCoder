"""子进程执行通用工具。

shell、python_exec、diagnostics、grep 共用同一个 Popen 进程组边界，统一处理
超时/取消、进程树回收、TimeoutExpired / OSError 和输出截断。
"""

from __future__ import annotations

import locale
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from leocoder.runtime.cancellation import CancellationToken
from leocoder.utils.text import truncate


@dataclass(slots=True)
class CommandResult:
    """子进程执行的统一结果类型。

    工具层可以直接把 CommandResult 转成 ToolResult，
    不用每个工具重复处理 exit_code、stdout/stderr 截断等逻辑。
    """

    exit_code: int
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    ok: bool
    error: str | None = None


def run_command(
    command: list[str] | str,
    *,
    cwd: Path,
    timeout_seconds: int = 30,
    max_output_chars: int = 20000,
    shell: bool = False,
    env: dict[str, str] | None = None,
    cancellation_token: CancellationToken | None = None,
) -> CommandResult:
    """执行子进程命令并返回统一结果。

    每个命令都在独立进程组中启动；超时或取消时终止整个进程组，并回收已经产生的输出。
    自动处理 TimeoutExpired 和 OSError，自动截断超长输出。
    这是 shell / python_exec / diagnostics / grep 四个工具共同需要的执行模式。
    """

    return _run_command_with_process_group(
        command,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        max_output_chars=max_output_chars,
        shell=shell,
        env=env,
        cancellation_token=cancellation_token,
    )


def _decode_output(data: bytes | str) -> str:
    """解码子进程输出，优先无乱码的候选编码。

    Windows 上 cmd.exe 的输出使用系统代码页（如中文环境的 GBK/cp936），直接按
    UTF-8 解码会把错误信息变成乱码。这里对固定候选编码逐次解码并比较替换字符
    （U+FFFD）数量，选择损失最小的一种：UTF-8 文本按 UTF-8 解，GBK 文本回退到
    gb18030，两种常见情况都能得到可读结果。
    """

    if isinstance(data, str):
        return data
    if not data:
        return ""
    candidates = []
    for enc in ("utf-8", locale.getpreferredencoding(False), "gb18030"):
        if enc not in candidates:
            candidates.append(enc)
    best: str | None = None
    best_loss: int | None = None
    for enc in candidates:
        try:
            # 归一化 CRLF：原 text=True 模式自带 universal newlines，二进制模式
            # 下需要手动把 Windows 子进程的 \r\n 转成 \n，保持既有测试契约。
            decoded = data.decode(enc, errors="replace").replace("\r\n", "\n")
        except LookupError:
            continue
        loss = decoded.count("\ufffd")
        if loss == 0:
            return decoded
        if best_loss is None or loss < best_loss:
            best, best_loss = decoded, loss
    return best if best is not None else data.decode("utf-8", errors="replace")


def _run_command_with_process_group(
    command: list[str] | str,
    *,
    cwd: Path,
    timeout_seconds: int,
    max_output_chars: int,
    shell: bool,
    env: dict[str, str] | None,
    cancellation_token: CancellationToken | None,
) -> CommandResult:
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=shell,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **_process_group_kwargs(),
        )
    except OSError as exc:
        return CommandResult(
            exit_code=-1,
            stdout="",
            stderr="",
            stdout_truncated=False,
            stderr_truncated=False,
            ok=False,
            error=f"命令执行失败：{exc}",
        )

    deadline = time.monotonic() + timeout_seconds
    timed_out = False
    interrupted = False
    stdout = stderr = ""
    while True:
        if cancellation_token is not None and cancellation_token.is_cancelled:
            interrupted = True
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        try:
            stdout, stderr = process.communicate(
                timeout=min(remaining, 0.05) if cancellation_token is not None else remaining,
            )
            break
        except subprocess.TimeoutExpired:
            if cancellation_token is None:
                timed_out = True
                break

    if interrupted or timed_out:
        _terminate_process_group(process)
        # communicate() again drains everything the process group emitted before
        # termination; this is the output that must accompany a timeout result.
        stdout, stderr = process.communicate()
    stdout = _decode_output(stdout)
    stderr = _decode_output(stderr)
    stdout, stdout_truncated = truncate(stdout, max_output_chars)
    stderr, stderr_truncated = truncate(stderr, max_output_chars)

    if interrupted:
        return CommandResult(
            exit_code=process.returncode if process.returncode is not None else -1,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            ok=False,
            error="命令已中断",
        )
    if timed_out:
        return CommandResult(
            exit_code=process.returncode if process.returncode is not None else -1,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            ok=False,
            error="命令执行超时",
        )

    ok = process.returncode == 0
    return CommandResult(
        exit_code=process.returncode if process.returncode is not None else -1,
        stdout=stdout,
        stderr=stderr,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        ok=ok,
    )


def _process_group_kwargs() -> dict[str, int | bool]:
    """Start each command in its own process group/session."""

    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _terminate_process_group(process: subprocess.Popen[str]) -> None:
    """Terminate the command and every descendant in its process group."""

    if os.name == "nt":
        _taskkill_process_tree(process.pid)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        return

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    # The leader may have exited while a descendant ignored SIGTERM.  Kill the
    # group unconditionally after the grace period so those descendants cannot
    # survive merely because Popen's direct child is already reaped.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if process.poll() is None:
        process.wait(timeout=1)


def _taskkill_process_tree(pid: int) -> None:
    """Best-effort Windows equivalent of killing a POSIX process group."""

    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    except OSError:
        pass
