from Interfaces import Base

class MetatypeDumper( Base ):
    """
        Interface for instance / method / function which allows
        dumping objects of a given metatype to the filesystem.

        Items which implement this interface will be registered
        with a Dumper, and used by its '_dumpObjects'.
    """
    def __call__( object, path=None ):
        """
        """
