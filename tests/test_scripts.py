import os
import stat
import subprocess
from pathlib import Path


def test_check_repo_visibility_script_parses_gh_output(tmp_path: Path):
    fake_gh = tmp_path / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "echo '{\"isPrivate\":false,\"visibility\":\"PUBLIC\",\"url\":\"https://github.com/example/repo\"}'\n",
        encoding="utf-8",
    )
    fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IEXEC)

    script = Path("scripts/check-repo-visibility.sh")
    result = subprocess.run(
        [str(script), "example/repo"],
        text=True,
        capture_output=True,
        env={**os.environ, "GH_BIN": str(fake_gh)},
    )

    assert result.returncode == 0
    assert "visibility=public" in result.stdout
    assert "is_private=false" in result.stdout
    assert "url=https://github.com/example/repo" in result.stdout
