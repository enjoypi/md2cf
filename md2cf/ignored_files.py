"""
Allow checking files for ignored status in mdignore files in the repo.
"""
from pathlib import Path
from typing import List

import gitignorefile

from md2cf.console_output import error_console


class GitRepository:
    """
    Represents a Git repository by finding the .git folder at the root
    of the tree. Note that there are cases where .git folders may exist
    in other parts of the tree. For example in terraform repositories
    the .terraform folder may contain copies of the tree including the .git
    folder. This can be handled by initializing the GitRepository from a
    known git root. After that all files will be correctly handled by the
    is_ignored() method.
    """

    def __init__(self, repo_path: Path, use_mdignore=True):
        self.use_mdignore = use_mdignore
        self.root_dir = self._find_root_dir(repo_path) if use_mdignore else None

    @staticmethod
    def _find_root_dir(start_path: Path):
        """
        Traverse the parents of the start_path until we find a .git directory
        :param start_path: A file or directory path to start searching from
        :return: The root directory of the git repo.
        """
        fs_root = Path("/")
        p = start_path.absolute()
        if p.is_file():
            p = p.parent
        while p != fs_root:
            git_dir = p.joinpath(".git")
            if git_dir.exists() and git_dir.is_dir():
                return p
            p = p.parent
        error_console.log(
            f":warning-emoji: Directory {start_path} is not part of a git "
            f"repository: mdignore checking disabled."
        )
        return None

    def collect_mdignores(self, filepath: Path) -> List[Path]:
        """
        Collect all .mdignore files from start location to the root of the
        repository. Filepath is assumed to be a subdirectory of the git root.
        If not, an error is printed and an empty list is returned.

        :param filepath: The path to start searching for .mdignore files
        :return: List of paths to .mdignore files relevant for start_path
        """
        fs_root = Path("/")
        ret = list()

        p = filepath.absolute()
        if p.is_file():
            p = p.parent
        while p != fs_root:
            mdignore_file = p.joinpath(".mdignore")
            if mdignore_file.exists() and mdignore_file.is_file():
                ret.append(mdignore_file)
            if p == self.root_dir:
                return ret
            p = p.parent

        # if not .git directory found, we're not in a git repo and mdignore files
        # cannot be trusted.
        return list()

    def is_ignored(self, filepath: Path) -> bool:
        """
        Check if filepath is ignored in the git repository by fetching all mdignores
        in the tree down to the git root and checking all of them.

        :param filepath: Path to the file to check if it is ignored.
        :return: True if the file is ignored in any .mdignore file
        """
        if not self.use_mdignore:
            return False
        if self.root_dir is None:
            return False
        mdignores = self.collect_mdignores(filepath)
        matchers = [gitignorefile.parse(str(g)) for g in mdignores]
        return any([m(str(filepath)) for m in matchers])
