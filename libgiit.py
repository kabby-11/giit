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

from object.object_utils import object_find, object_read
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
                   help="Specify the type of the object to create.")]
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