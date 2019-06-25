""" FSDump plugin interface:  MetatypeDumper

$Id: MetatypeDumper.py 97084 2005-04-29 14:19:31Z tseaver $
"""

try:
    from zope.interface import Interface
except ImportError: # Zope < 2.8.0a2
    from Interfaces import Interface

class MetatypeDumper( Interface ):
    """
        Interface for instance / method / function which allows
        dumping objects of a given metatype to the filesystem.

        Items which implement this interface will be registered
        with a Dumper, and used by its '_dumpObjects'.
    """
    def __call__( object, path=None ):
        """
        """
