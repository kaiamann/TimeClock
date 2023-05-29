"""Module taking care of version control"""
from git import Repo, InvalidGitRepositoryError

class VersionControl:
    """Class taking care of version control"""

    def __init__(self, data_dir: str) -> None:
        self.repo = Repo(data_dir)
        if not self.repo.remotes:
            raise InvalidGitRepositoryError(f"""The git repository at \
            {data_dir} does not seem to have a remote.""")

        # take the first remote
        self.remote = self.repo.remotes[0]

    def commit(self):
        """Commit changes to the data repo"""
        # get changed files
        changed_files = list(item.a_path for item in self.repo.index.diff(None))
        if len(changed_files) < 1:
            print("Nothing to commit. Aborting")
            return

        # add modified files
        self.repo.index.add(changed_files)
        # and commit
        self.repo.index.commit("Updated working hours")
        print(self.repo.head.commit.message)

    def push(self):
        """Push to remote."""
        self.repo.git.push()

    def pull(self):
        """Pull from remote."""
        self.repo.git.pull()

    def fetch(self):
        """Fetch latest version from remote."""
        self.remote.fetch()

    def is_behind(self):
        """Check if the repo is behind the origin.

        Returns:
            bool: True if repo is behind, false otherwise.
        """
        # see if we're behind the remote
        commits_behind = self.repo.iter_commits('main..origin/main')
        return sum(1 for _ in commits_behind) > 0
