from pathlib import Path
import subprocess
import shutil
from collections.abc import Callable
from git import Repo, rmtree


class ReleaseSafeUtils:
    def __init__(self, release_path: Path) -> None:
        self.release_path = release_path

    def __check_path_in_release(self, path: Path) -> None:
        if not path.resolve().is_relative_to(self.release_path.resolve()):
            err_msg = f"Путь {path.resolve()} должен быть внутри папки выпуска {self.release_path.resolve()}"
            raise Exception(err_msg)

    def __check_path_not_nested(self, *, not_nested: Path, in_path: Path) -> None:
        if not_nested.resolve().is_relative_to(in_path.resolve()):
            err_msg = f"Путь {not_nested.resolve()} не должен быть внутри папки {in_path.resolve()}"
            raise Exception(err_msg)

    def mkdir_safe(self, path: Path, *, exist_ok: bool = False) -> None:
        self.__check_path_in_release(path)
        path.mkdir(exist_ok=exist_ok)

    def rmtree_safe(self, path: Path) -> None:
        self.__check_path_in_release(path)
        rmtree(path.resolve())

    def copytree_safe(
        self, src: Path, dst: Path, *, ignore: Callable[[str, list[str]], list[str]] | None = None
    ) -> None:
        self.__check_path_in_release(dst)
        self.__check_path_not_nested(not_nested=dst, in_path=src)
        shutil.copytree(src.resolve(), dst.resolve(), ignore=ignore)

    def copyfile_safe(self, src: Path, dst: Path) -> None:
        self.__check_path_in_release(dst)
        shutil.copyfile(src.resolve(), dst.resolve())

    def copy_repo_files_safe(self, src_repo: Repo, dst_path: Path) -> None:
        src_git_path = Path(src_repo.git_dir).resolve()
        src_path = src_git_path.parent
        dst_path = dst_path.resolve()

        self.__check_path_in_release(dst_path)
        self.__check_path_not_nested(not_nested=src_path, in_path=dst_path)

        if dst_path.exists():
            self.rmtree_safe(dst_path)

        for item_path, _staged in src_repo.index.entries:
            src_item_path = src_path / item_path
            dst_item_path = dst_path / item_path

            if src_item_path.is_dir():
                continue
            if src_item_path.is_relative_to(src_git_path):
                continue
            if src_item_path.is_relative_to(self.release_path):
                continue

            if src_item_path.exists():
                dst_item_path.parent.mkdir(parents=True, exist_ok=True)
                self.copyfile_safe(src_item_path, dst_item_path)

        for item_path in src_repo.untracked_files:
            src_item_path = src_path / item_path
            dst_item_path = dst_path / item_path

            if src_item_path.is_dir():
                continue
            if src_item_path.is_relative_to(src_git_path):
                continue
            if src_item_path.is_relative_to(self.release_path):
                continue

            if src_item_path.exists():
                dst_item_path.parent.mkdir(parents=True, exist_ok=True)
                self.copyfile_safe(src_item_path, dst_item_path)

    def zip_dir_safe(self, *, src_dir: Path, dst_zipfile: Path) -> None:
        self.__check_path_not_nested(not_nested=dst_zipfile, in_path=src_dir)
        res_file = Path(
            shutil.make_archive(
                base_name=str(dst_zipfile.with_suffix("")),
                format="zip",
                root_dir=str(src_dir),
            )
        )
        if res_file.exists() and not res_file.is_dir():
            res_file.rename(res_file.with_suffix("").with_suffix(dst_zipfile.suffix))


def build_release_git_remote(
    *,
    dev_repo_path: Path,
    release_repo_url: str | None,
    release_repo_branch: str | None = None,
    release_path: Path,
    release_dev_repo_path: Path,
    func_before_dev_repo_clone: Callable[[ReleaseSafeUtils], None] | None = None,
    func_after_dev_repo_clone: Callable[[ReleaseSafeUtils], None] | None = None,
) -> ReleaseSafeUtils:
    """
    Создание выпуска в формате удаленного репозитория,
    содержащего копию исходного кода из локального репозитория разработчика

    Удаленный репозиторий - репозиторий на стороне заказчика (например, в среде разработки заказчика)

    Удаленный репозиторий отличается от локального тем, что кроме исходного кода содержит файлы,\
    специфичные для среды заказчика. Например: Dockerfile, предопределенные файлы конфигурации

    Аргументы:
        dev_repo_path - путь к локальному репозиторию разработчика, например "./"

        release_repo_url - url удаленного репозитория

        release_repo_branch - ветка в репозитории выпуска, если None, то исп. текущая ветка репозитория разработчика

        release_path - путь к локальной папке, в которой должен быть создан выпуск, например "./.release"

        release_dev_repo_path - путь к папке, в которой должна находится копия исходного кода
        из локального репозитозитория резработчика, например "./release/src"
        Путь, указанный в release_dev_repo_path, должен находится внути пути release_path

        func_before_dev_repo_clone - функция, выполняющаяся перед копированием исходного кода
        из локального репозитория разработчика в папку выпуска.
        Используется, например, для автообновления документации

        func_after_dev_repo_clone - функция, выполняющаяся после копирования исходного кода
        из локального репозитория разработчика в папку выпуска.
        Используется, например, для добавления доп. артефактов в выпуск
    """

    dev_repo_path = dev_repo_path.resolve()
    release_path = release_path.resolve()
    release_dev_repo_path = release_dev_repo_path.resolve()
    release_safe_utils = ReleaseSafeUtils(release_path=release_path)
    uv_path = shutil.which("uv")

    ########################################
    if release_path == dev_repo_path:
        err_msg = f"Путь в аргументе release_path ({release_path}) не может совпадать с dev_repo_path ({dev_repo_path})"
        raise Exception(err_msg)

    if dev_repo_path.is_relative_to(release_path):
        err_msg = f"Путь в аргументе dev_repo_path ({dev_repo_path}) не может быть внутри release_path ({release_path})"
        raise Exception(err_msg)

    if not release_path.is_relative_to(dev_repo_path):
        err_msg = f"Путь в аргументе release_path ({release_path}) должен быть внутри dev_repo_path ({dev_repo_path})"
        raise Exception(err_msg)

    if not release_dev_repo_path.is_relative_to(release_path):
        err_msg = (
            f"Путь в аргументе release_dev_repo_path ({release_dev_repo_path})"
            f" должен быть внутри release_path ({release_path})"
        )
        raise Exception(err_msg)

    if not uv_path:
        err_msg = "не найден uv"
        raise Exception(err_msg)

    ########################################
    Path.mkdir(release_path, exist_ok=True)

    if release_repo_url and not (release_path / ".git").exists():
        print(f"Клонирование удаленного репозитория {release_repo_url} (clone --depth=1 --no-single-branch)")
        Repo.clone_from(release_repo_url, release_path, allow_unsafe_protocols=True, depth=1, no_single_branch=True)

    ########################################
    dev_repo = Repo(dev_repo_path)
    release_repo = Repo(release_path)
    release_repo_branch = release_repo_branch or dev_repo.active_branch.name

    if release_repo_url:
        if not release_repo.remotes.origin.url or release_repo.remotes.origin.url != release_repo_url:
            err_msg = (
                f"URL удаленного репозитория {release_repo.remotes.origin.url}"
                f"не соответствует URL в аргументе release_repo_url ({release_repo_url})"
            )
            raise Exception(err_msg)

        print(f"Загрузка новых изменений и веток из удаленного репозитория {release_repo_url} (fetch --depth=1 )")
        fetch_res = release_repo.remotes.origin.fetch(allow_unsafe_protocols=True, depth=1)
        for fetch_info in fetch_res:
            print(f"Загружена ветка {fetch_info.ref}")

    if release_repo_branch != release_repo.active_branch.name:
        if release_repo_url and release_repo_branch in release_repo.remotes.origin.refs:
            print(f"Переключение на удаленную ветку {dev_repo.active_branch}")
            release_repo.git.switch(release_repo_branch)
            release_repo.active_branch.set_tracking_branch(release_repo.remotes.origin.refs[release_repo_branch])
        elif release_repo_branch in release_repo.heads:
            print(f"Переключение на локальную ветку {dev_repo.active_branch}")
            release_repo.git.switch(release_repo_branch)
        else:
            print(f"Создание новой локальной ветки {dev_repo.active_branch}")
            release_repo.git.switch("-c", release_repo_branch)

    if release_repo.active_branch.is_remote():
        print(f"Вытягивание изменений из удаленного репозитория {release_repo_url} (pull --ff-only --depth 1)")
        pull_res = release_repo.remotes.origin.pull(allow_unsafe_protocols=True, ff_only=True, depth=1)
        for pull_info in pull_res:
            print(f"Обновлена ветка {pull_info.ref}")

    ########################################
    print(f"Создание requirements.txt в {release_path}")
    print(
        subprocess.check_output(  # noqa S603
            [
                uv_path,
                "export",
                "--format",
                "requirements.txt",
                "-o",
                release_path / "requirements.txt",
                "--no-dev",
                "--quiet",
                "--frozen",
                "--no-hashes",
                "--no-editable",
                "--no-emit-local",
            ],
            text=True,
            cwd=Path.cwd(),
        )
    )

    ########################################
    if func_before_dev_repo_clone:
        func_before_dev_repo_clone(release_safe_utils)
    ########################################

    print(f"Копирование файлов локального репозитория в {release_dev_repo_path}")
    release_safe_utils.copy_repo_files_safe(dev_repo, release_dev_repo_path)

    ########################################
    if func_after_dev_repo_clone:
        func_after_dev_repo_clone(release_safe_utils)
    ########################################

    return release_safe_utils
