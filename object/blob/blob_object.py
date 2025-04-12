from object.git_object import GitObject


class GitBlob(GitObject):
    """A Git blob object."""

    format = b'blob'

    def serialize(self, data):
        """Serialize the blob object."""
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data