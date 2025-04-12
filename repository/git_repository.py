import configparser
import os
from repository.repo_utils import repo_file


class GitRepository (object):
    """Git Repository class."""

    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force = False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not(force or os.path.isdir(self.gitdir)):
            raise Exception("Not a git repository: " + path)
        
        #As there is  a config file in the .git directory, we can assume that this is a git repository
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration file missing" )
        
        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion", fallback=0))
            if vers != 0:
                raise Exception("Unsupported repository format version: " + str(vers))
