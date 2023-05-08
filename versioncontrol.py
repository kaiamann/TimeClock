import git

class VersionControl:

    def __init__(self) -> None:
        # self.repo = git.Repo("path")
        pass
    
    def commit(self):
        pass

    def push(self):
        pass

    def pull(self):
        pass

    def fetch():
        pass

    def test(self):
        print("test")


def isBehind(repo: git.Repo):
    # see if we're behind the remote
    commits_behind = repo.iter_commits('main..origin/main')
    return sum(1 for _ in commits_behind) > 0

def getGitRepoWithRemote(path: str):
    remote = None
    try:
        repo = git.Repo(path)
    except git.InvalidGitRepositoryError:
        print("%s is not a git repository. Git functionality not available." % (path))
        return repo

    # also check if there is a remote
    if not repo.remotes:
        print("The git repository at %s does not seem to have a remote. Git functionality not available." % (path))
        return repo

    remote = repo.remotes[0]
    # fetch from remote
    remote.fetch()

    return repo


    def commit(self):
        # get changed files
        changedFiles = list(item.a_path for item in self.repo.index.diff(None))
        if len(changedFiles) < 1:
            print("Nothing to commit. Aborting")
            return

        if isBehind(self.repo):
            print("Your repo seems to be behind the remote. Please pull first.")

        # add modified files
        self.repo.index.add(changedFiles)
        # and commit
        self.repo.index.commit("Added working hours for %s" % (formatDate(date.today())))
        print(self.repo.head.commit.message)

    def push(self):
        self.repo.git.push()