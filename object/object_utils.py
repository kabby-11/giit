""" Read object sha from Git repository 'repo'.
    Return the object as a byte string.
    The sha is a 40-character hexadecimal string.
    We will fetch two things from sha : object type and object size.
    And these object could be any of the following types:
    - commit
    - tree
    - blob
    - tag
    """

import hashlib
import os
import zlib
from repository.repo_utils import repo_file, repo_path


def object_read(repo, sha):

    """To read an object, we need to know its SHA-1 hash. 
    We then compute its path from this hash (with the formula explained above: 
    first two characters, then a directory delimiter /, then the remaining part) and 
    look it up inside of the “objects” directory in the gitdir. 
    sha[0:2] = e6
    sha[2:] = 73d1b7eaa0aa01b5bc2442d570a765bdaae751
    That is, the path to e673d1b7eaa0aa01b5bc2442d570a765bdaae751 is .git/objects/e6/73d1b7eaa0aa01b5bc2442d570a765bdaae751."""

    path = repo_path(repo, "objects", sha[0:2], sha[2:])

    if not os.path.exists(path):
        return None
    
    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())
        # The first four bytes are the size of the object
        #Example of raw: b'blob 12\x00Hello world!'
        # The rest is the object itself
        # The first four bytes are the type of the object

        x = raw.find(b' ') # find the first space
        format = raw[:x] # The type of the object

        y = raw.find(b'\x00',x) # find the first null byte
        #raw[x:y] = b'12'
        #raw[x:y].decode("ascii") = '12'
        #int(raw[x:y].decode("ascii")) = 12
        size = int(raw[x:y].decode("ascii")) # The size of the object

        if(size != len(raw) - y -1):
            raise Exception("Object size mismatch: " + sha)


        #Pick constructor according to the type of the object
        match format:
            case b'commit' : c=GitCommit
            case b'tree'   : c=GitTree
            case b'blob'   : c=GitBlob
            case b'tag'    : c=GitTag
            case _         : raise Exception("Unknown object type: " + format.decode("ascii"))

        return c(raw[y+1:])
    

#now we will create how to write the object
def object_write(obj, repo = None):
    #Serialize the object
    data = obj.serialize()

    result = obj.format + b' ' + str(len(data)).encode("ascii") + b'\x00' + data

    #Compute the sha1 hash of the object
    sha = hashlib.sha1(result).hexdigest()

    if repo:
        #If there is a repository, we will create a path for it
        path = repo_file(repo, "objects", sha[0:2], sha[2:], mkdir = True)

        #If the path doesn't exist, we will create it
        #and write the object to it
        #The path is the sha1 hash of the object
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(zlib.compress(result))
        
    return sha

def object_find(repo, name, format=None, follow=True):
    return name

def object_hash(f, format, repo = None):
    data = f.read()

    #Compute the sha1 hash of the object
    match format:
        case b'commit' : c=GitCommit
        case b'tree'   : c=GitTree
        case b'blob'   : c=GitBlob
        case b'tag'    : c=GitTag
        case _         : raise Exception("Unknown object type: " + format.decode("ascii"))

    return object_write(c, repo)