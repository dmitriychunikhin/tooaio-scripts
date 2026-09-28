from pathlib import Path
from toooaio_scripts.build_release_git_remote import build_release_git_remote


def test() -> None:
    dev_repo_path = Path(".")
    release_repo_url = ""
    release_repo_branch = "release"
    release_path = Path(".release")
    release_dev_repo_path = release_path / "src"
    release_safe_utils = build_release_git_remote(
        dev_repo_path=dev_repo_path,
        release_repo_url=release_repo_url,
        release_repo_branch=release_repo_branch,
        release_path=release_path,
        release_dev_repo_path=release_dev_repo_path,
    )

    release_safe_utils.zip_dir_safe(src_dir=release_dev_repo_path, dst_zipfile=release_path / "test.zip")


if __name__ == "__main__":
    test()
