import argparse
import configparser
from datetime import datetime
import grp
from fnmatch import fnmatch
import hashlib
from math import ceil
import os
import re
import sys
import zlib

from object.object_utils import object_find, object_hash, object_read
from repository.git_repository import GitRepository
from repository.repo_utils import repo_create, repo_default_config, repo_dir, repo_file, repo_find


argparser = argparse.ArgumentParser(description="The best content tracker")
argsubparsers = argparser.add_subparsers(title="Commands" ,dest="command")
argsubparsers.required = True

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case "add"          : cmd_add(args)
        case "cat-file"     : cmd_cat_file(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "checkout"     : cmd_checkout(args)
        case "commit"       : cmd_commit(args)
        case "hash-object"  : cmd_hash_object(args)
        case "init"         : cmd_init(args)
        case "log"          : cmd_log(args)
        case "ls-files"     : cmd_ls_files(args)
        case "ls-tree"      : cmd_ls_tree(args)
        case "rev-parse"    : cmd_rev_parse(args)
        case "rm"           : cmd_rm(args)
        case "show-ref"     : cmd_show_ref(args)
        case "status"       : cmd_status(args)
        case "tag"          : cmd_tag(args)
        case _              : print("Bad command.")


    repo = GitRepository(args.path, True)

    #Creating the .git directory
    assert repo_dir(repo, "branches", mkdir = True)
    assert repo_dir(repo, "objects", mkdir = True)
    assert repo_dir(repo, "refs", "tags", mkdir = True)
    assert repo_dir(repo, "refs", "heads", mkdir = True)

    # .git/description
    with open(repo_file(repo, "description"), "w") as f:
        f.write("Unnamed repository; edit this file 'description' to name the repository.\n")
    
    # .git/HEAD 
    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")
            
    # And lastly for .git/config
    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo


# Command : git init
argsp = argsubparsers.add_parser("init", help="Create an empty git repository")
argsp.add_argument("path", 
                   metavar="directory",
                   default=".",
                   help="Where to create the repository.",
                   nargs = "?")

def cmd_init(args):
    repo_create(args.path)


# Command : git cat-file blob e0695f14a412c29e252c998c81de1dde59658e4a
argsp = argsubparsers.add_parser("cat-file", help="Show information about a git object")

argsp.add_argument("type",
                     metavar="type",
                     choices=["commit", "tree", "blob", "tag"],
                     help="Specify the type of the object to show.")

argsp.add_argument("object",
                     metavar="object",
                     help="The object to show.")

def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo,args.object, format = args.type.encode())

def cat_file(repo, obj, format = None):
    obj = object_read(repo, object_find(repo, obj, format=format))
    sys.stdout.buffer.write(obj.serialize())

# Command : git hash-object [-w] [-t TYPE] FILE
argsp = argsubparsers.add_parser("hash-object", 
                                 help="Compute the object ID and optionally create a blob from a file")

argsp.add_argument("-w", 
                   dest="write",
                   action="store_true",
                   help="Write the object into the database")
argsp.add_argument("-t",
                   metavar="type",  
                   choices=["commit", "tree", "blob", "tag"], 
                   default="blob",
                   help="Specify the type of the object to create.")
argsp.add_argument("path",
                    metavar="file",
                    help="The file to hash.")

def cmd_hash_object(args):
    if(args.write):
        repo = repo_find()
    else : 
        repo = None

    with open(args.path, "rb") as f:
        sha = object_hash(f, args.type.encode(), repo)
        print(sha)

def kvlm_parse(raw, start=0, dct=None):
    if not dct:
        dct = dict()
        # You CANNOT declare the argument as dct=dict() or all call to
        # the functions will endlessly grow the same dict.

    # This function is recursive: it reads a key/value pair, then call
    # itself back with the new position.  So we first need to know
    # where we are: at a keyword, or already in the messageQ

    # We search for the next space and the next newline.
    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)

    # If space appears before newline, we have a keyword.  Otherwise,
    # it's the final message, which we just read to the end of the file.

    # Base case
    # =========
    # If newline appears first (or there's no space at all, in which
    # case find returns -1), we assume a blank line.  A blank line
    # means the remainder of the data is the message.  We store it in
    # the dictionary, with None as the key, and return.
    if (spc < 0) or (nl < spc):
        assert nl == start
        dct[None] = raw[start+1:]
        return dct

    # Recursive case
    # ==============
    # we read a key-value pair and recurse for the next.
    key = raw[start:spc]

    # Find the end of the value.  Continuation lines begin with a
    # space, so we loop until we find a "\n" not followed by a space.
    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '): break

    # Grab the value
    # Also, drop the leading space on continuation lines
    value = raw[spc+1:end].replace(b'\n ', b'\n')

    # Don't overwrite existing data contents
    if key in dct:
        if type(dct[key]) == list:
            dct[key].append(value)
        else:
            dct[key] = [ dct[key], value ]
    else:
        dct[key]=value

    return kvlm_parse(raw, start=end+1, dct=dct)

#kvlm is a dictionary with the keys being the keywords and the values
# being the values. The key None is reserved for the message.
def kvlm_serialize(kvlm):

    ret = b''

    for k in kvlm.keys():
        if k is None:
            continue
        val = kvlm[k]
        #NORMALIZE TO A LIST
        if type(val) != list:
            val = [val]
        for v in val:
            ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'
    
    ret += b'\n' + kvlm[None]

    return ret

# Command : git log 
argsp = argsubparsers.add_parser("log", help="Show the history of a given commit")
argsp.add_argument("commit",
                    metavar="HEAD",
                    help="The object to show.",
                    nargs = "?")

def cmd_log(args):
    repo = repo_find()
    print("digraph giitlog")
    print("node[shape=react]")

def log_graphviz(repo, sha ,seen):
    if sha in seen:
        return
    seen.add(sha)
    commit = object_read(repo, sha)
    message = commit.kvlm[None].decode("utf-8").strip()
    message = message.replace("\\", "\\\\")
    message = message.replace("\"", "\\\"")

    if "\n" in message : 
        message = message[: message.index("\n")]
    
    print(f" c_{sha} [label=\"[sha[0:7] : {message}\"]")
    assert commit.format == b'commit'
    
    if not b'parent' in commit.kvlm.keys():
        return

    parents = commit.kvlm[b'parent']

    if type(parents) != list:
        parents = [parents]
    

    for p in parents:
        p = p.decode("utf-8")
        print(f" c_{sha} -> c_{p}")
        log_graphviz(repo, p, seen)

# Command : git ls-tree [-r] [tree-ish]
argsp = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object.")
argsp.add_argument("-r",
                   dest="recursive",
                   action="store_true",
                   help="Recurse into sub-trees")

argsp.add_argument("tree",
                   help="A tree-ish object.")

def cmd_ls_tree(args):
    repo = repo_find()
    ls_tree(repo, args.tree, args.recursive)

def ls_tree(repo, ref, recursive=None, prefix=""):
    sha = object_find(repo, ref, fmt=b"tree")
    obj = object_read(repo, sha)
    for item in obj.items:
        if len(item.mode) == 5:
            type = item.mode[0:1]
        else:
            type = item.mode[0:2]

        match type: # Determine the type.
            case b'04': type = "tree"
            case b'10': type = "blob" # A regular file.
            case b'12': type = "blob" # A symlink. Blob contents is link target.
            case b'16': type = "commit" # A submodule
            case _: raise Exception(f"Weird tree leaf mode {item.mode}")

        if not (recursive and type=='tree'): # This is a leaf
            print(f"{'0' * (6 - len(item.mode)) + item.mode.decode("ascii")} {type} {item.sha}\t{os.path.join(prefix, item.path)}")
        else: # This is a branch, recurse
            ls_tree(repo, item.sha, recursive, os.path.join(prefix, item.path))