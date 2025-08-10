#!/usr/bin/env python3
"""
Subprocess sandbox utilities: kill process trees and enforce CPU/RAM timeouts.
Unix-only limits via resource; cross-platform best-effort.
"""

import os
import signal
import subprocess
import time
from typing import Optional


def kill_process_tree(pid: int) -> None:
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def run_with_limits(cmd: list, timeout: int = 30, memory_mb: Optional[int] = None) -> subprocess.CompletedProcess:
    preexec = None
    try:
        import resource

        def set_limits():
            # Put in a new process group so we can kill the tree easily
            os.setsid()
            if memory_mb:
                bytes_limit = memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (bytes_limit, bytes_limit))
                resource.setrlimit(resource.RLIMIT_DATA, (bytes_limit, bytes_limit))

        preexec = set_limits
    except Exception:
        # Windows / unsupported: still set new session
        def setpg():
            os.setsid()
        preexec = setpg

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=preexec)
    start = time.time()
    try:
        outs, errs = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, outs, errs)
    except subprocess.TimeoutExpired:
        kill_process_tree(proc.pid)
        return subprocess.CompletedProcess(cmd, -1, "", f"Timed out after {timeout}s")

