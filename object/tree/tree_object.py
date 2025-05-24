from object.git_object import GitObject
from object.tree.tree_utils import tree_parse, tree_serialize


class GitTree(GitObject):

    format = b'tree'

    def deserialize(self, data):
        self.items = tree_parse(data)

    def serialize(self):
        return tree_serialize(self)
    
    def init(self):
        self.items = list()