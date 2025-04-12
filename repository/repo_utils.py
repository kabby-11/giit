#THIS IS THE STRUCTURTRE WE ARE CREATING FOR OUR REPOSITORY
# .git/
# ├── **objects/**
# │   ├── [first two characters of SHA-1]/
# │   │   └── [remaining 38 characters of SHA-1]
# │   └── **pack/**
# │       ├── [packfile name].pack
# │       └── [packfile name].idx
# ├── **refs/**
# │   ├── **heads/**
# │   │   └── [branch name]
# │   └── **tags/**
# │       └── [tag name]
# ├── **HEAD**
# ├── **config**
# ├── description
# ├── branches/
# └── info/
#     └── exclude


import configparser
import os
from repository.git_repository import GitRepository


def repo_path(repo, *path):
    """Return the path to a file in the git repository."""
    return os.path.join(repo.gitdir, *path)

def repo_dir(repo, *path, mkdir = False):
    """Same as repo_path, but creates the directory if it doesn't exist."""
    path = repo_path(repo, *path)

    if os.path.exists(path):
        if(os.path.isdir(path)):
            return path
        else:
            raise Exception("Path is not a directory: " + path)
    
    if mkdir:
        os.makedirs(path)
        return path 
    else:
        return None

def repo_file(repo, *path, mkdir = False):
    """Same as repo_path, but create dirname(*path) if absent.  For
example, repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create
.git/refs/remotes/origin."""

    if repo_dir(repo, *path[:-1], mkdir = mkdir):
        return repo_path(repo, *path)

def repo_create(path):
    """Create a new git repository in the given path."""

    repo = GitRepository(path, True)
    #Making sure the path either doesn't exist or is an empty directory"""

    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception("Path is not a directory: " + path)
        if os.path.exists(repo.gitdir) and os.listdir(repo.worktree):
            raise Exception("Directory not empty: " + path)
    else:
        os.makedirs(repo.worktree)


def repo_default_config():
    """Return the default configuration for a git repository."""
    config = configparser.ConfigParser()
    config.add_section("core")
    config.set("core", "repositoryformatversion", "0")
    config.set("core", "filemode", "false")
    config.set("core", "bare", "false")

    return config

def repo_find(path = ".", required = True):
    path = os.path.realpath(path) #get the path uptill the root directory of the project
                                  #E.g. /home/user/project
    if os.path.isdir(path):
        return GitRepository(path)
    
    #If the path is not a directory, we need to check the parent directory 
    parent = os.path.realpath(os.path.join(path, ".."))
    if parent == path:
        if required:
            raise Exception("Not a git repository: " + path)
        else:
            return None
    
    #recursively check the parent directory
    return repo_find(parent, required)