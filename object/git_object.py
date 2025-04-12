class GitObject (object):

    def __init__(self, data = None):
        if data != None:
            self.deserialize(data)
        else:
            self.init()

    def serialize(self, data):
        """This function MUST be implemented by subclasses.

It must read the object's contents from self.data, a byte string, and
do whatever it takes to convert it into a meaningful representation.
What exactly that means depend on each subclass.

        """
        raise Exception("Unimplemented method serialize() in GitObject class")
    def deserialize(self, data):
        raise Exception("Unimplemented method deserialize() in GitObject class")
    def init(self):
        pass