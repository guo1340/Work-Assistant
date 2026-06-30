from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any


@dataclass(frozen=True)
class RequestBranch:
    name: str
    base_branch: str
    base_sha: str


class GitSafety:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._branches: dict[str, RequestBranch] = {}

    def prepare(self, request_id: str) -> RequestBranch:
        existing = self._branches.get(request_id)
        if existing:
            return existing
        base_branch = self._run("branch", "--show-current")
        if not base_branch:
            raise RuntimeError("Git repository has no active branch")
        base_sha = self._run("rev-parse", "HEAD")
        branch_name = f"devflow/{request_id}"
        branches = self._run("branch", "--list", branch_name)
        if branches:
            self._run("switch", branch_name)
        else:
            self._run("switch", "-c", branch_name)
        branch = RequestBranch(branch_name, base_branch, base_sha)
        self._branches[request_id] = branch
        return branch

    def apply_and_commit(
        self,
        request_id: str,
        changes: dict[str, str],
    ) -> str:
        branch = self.prepare(request_id)
        current = self._run("branch", "--show-current")
        if current != branch.name:
            self._run("switch", branch.name)
        for relative, content in changes.items():
            target = (self.root / relative).resolve()
            if self.root not in target.parents:
                raise ValueError(f"change escapes project root: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
        self._run("add", "--", *changes.keys())
        if not self._run("status", "--short"):
            return self._run("rev-parse", "HEAD")
        self._run("commit", "-m", f"DevFlow {request_id}")
        return self._run("rev-parse", "HEAD")

    def reject(self, request_id: str) -> None:
        branch = self._branches.get(request_id)
        if branch is None:
            return
        current = self._run("branch", "--show-current")
        if current == branch.name:
            self._run("switch", branch.base_branch)
        self._run("branch", "-D", branch.name)
        self._branches.pop(request_id, None)

    def snapshot(self) -> dict[str, Any]:
        return {
            request_id: {
                "name": branch.name,
                "base_branch": branch.base_branch,
                "base_sha": branch.base_sha,
            }
            for request_id, branch in self._branches.items()
        }

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Git command failed")
        return result.stdout.strip()
