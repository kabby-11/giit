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
from object.refs.refs_utils import GitTag, ref_list
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

argsp = argsubparsers.add_parser("checkout", help="Checkout a commit inside of a directory")
argsp.add_argument("commit",
                    metavar="commit",
                    help="The commit to checkout.")
argsp.add_argument("path",
                   help="The EMPTY directory to checkout into.")

def cmd_checkout(args):
    repo = repo_find()

    obj = object_read(repo, object_find(repo, args.commit))

    if obj.format == b'commit':
        obj = object_read(repo, obj.kvlm[b'tree'].decode("ascii"))

    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception(f"Not a directory: {args.path}!")
        if os.listdir(args.path):
            raise Exception(f"Not empty {args.path}!")
    else:
        # Create the directory if it doesn't exist
        os.makedirs(args.path)    

    tree_checkout(repo, obj, os.path.realpath(args.path))

def tree_checkout(repo, tree, path):
    for item in tree.items:
        obj = object_read(repo, item.sha)
        dest = os.path.join(path, item.path)

        if obj.fmt == b'tree':
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b'blob':
            # @TODO Support symlinks (identified by mode 12)
            with open(dest, "wb") as f:
                f.write(obj.blobdata)


# Command : git show-ref

argsp = argsubparsers.add_parser("show-ref", help="List references in the repository")

def cmd_show_ref(args):
    repo = repo_find()
    refs = ref_list(repo)
    show_ref(repo, refs,prefix = "refs")

def show_ref(repo, refs, with_hash = True, prefix = ""):
    if prefix:
        prefix += "/"
    for k, v in refs.items():
        if type(v) == str and with_hash:
            print (f"{v} {prefix}{k}")
        elif type(v) == str:
            print (f"{prefix}{k}")
        else:
            show_ref(repo, v, with_hash = with_hash, prefix = f"{prefix}{k}" )

# Command : git tag | git tag NAME [OBJECT] | git tag -a NAME [OBJECT]
argsp = argsubparsers.add_parser("tag", help ="List and Create tags")

argsp.add_argument("-a",
                   action="store_true",
                   dest="create_tag_object",
                   help="Whether to creta a tag object")
argsp.add_argument("name",
                   nargs="?",
                   help="The name of the tag to create.")
argsp.add_argument("object",
                    default="HEAD",
                    nargs="?",
                    help="The object to tag. If not specified, HEAD is used.")

def cmd_tag(args):
    repo = repo_find()

    if not args.name:
        refs = ref_list(repo)
        show_ref(repo, refs, with_hash = False)
        return

    else: 
        tag_create(repo, args.name, args.object, create_tag_object = args.create_tag_object)

def tag_create(repo, name, obj, create_tag_object = False):
    sha = object_find(repo, ref)

    if create_tag_object:
        # Create a tag object (commit)
        tag = GitTag()
        tag.kvlm = dict()
        tag.kvlm[b'tag'] = name.encode("utf-8")
        tag.kvlm[b'object'] = sha.encode("utf-8")
        tag.kvlm[b'type'] = b'commit'
        tag.kvlm[b'tagger'] = b'Giit <giit@example.com>'
        tag.kvlm[None] = b'Tag is generated by Giit'

        tag_sha = object_write(tag, repo)
        ref_create(repo, "tags/" + name, tag_sha)
    else:
        # Create a reference to the object
        ref_create(repo, "tags/" + name, sha)

def ref_create(repo, ref, sha):
    path = repo_file(repo, ref)
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    
    with open(path, 'w') as f:
        f.write(sha + "\n")
    
    print(f"Created reference {ref} to {sha}")  