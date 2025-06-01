import os
from object.commit.commit_object import GitCommit
from repository.repo_utils import repo_dir, repo_file

class GitTag(GitCommit):
    fmt = b'tag'

def ref_resolve(repo, ref):

    path = repo_file(repo, ref)
    # Resolve a reference in a case when we're looking for HEAD on a new repo
    # but with no commits yet. In that case, .git/HEAD is not present.

    if not os.path.exists(path):
        return None
    
    with open(path, 'r') as f:
        data = f.read()[:-1] # Remove trailing newline
    
    if data.startswith("ref: "):
        return ref_resolve(repo, data[5:])
    else:
        return data
    
def ref_list(repo, path = None):
    if not path:
        path = repo_dir(repo, "refs")
    ret = dict()
    #As the refs shown by Git are sorted, we will do the same
    for f in sorted(os.listdir(path)):
        can = os.path.join(path,f)
        if os.path.isdir(can):
            ret[f] = ref_list(repo, can)
        else:
            with open(can, 'r') as file:
                ret[f] = ref_resolve(repo, can)

    return ret