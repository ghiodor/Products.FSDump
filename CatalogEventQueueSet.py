""" Classes: CatalogEventQueueSet

$Id$
"""
from __future__ import generators

from Interface import Interface

from Persistence import Persistent

from Products.QueueCatalog.CatalogEventQueue import CatalogEventQueue
from Products.QueueCatalog.CatalogEventQueue import EVENT_TYPES
from Products.QueueCatalog.CatalogEventQueue import ADDED_EVENTS
from Products.QueueCatalog.CatalogEventQueue import ADDED
from Products.QueueCatalog.CatalogEventQueue import CHANGED
from Products.QueueCatalog.CatalogEventQueue import CHANGED_ADDED
from Products.QueueCatalog.CatalogEventQueue import REMOVED

class ICatalogEventQueueSetDelegate( Interface ):

    """ Interface for the "store" underlying a CEQS.
    """

    def hasUID( uid ):

        """ Do we already have UID?
        """

    def add( uid ):

        """ Add UID to the store.

        o Delegate is responsible for finding object using UID.
        """

    def change( uid ):

        """ Update UID within the store.

        o Delegate is responsible for finding object using UID.
        """

    def remove( uid ):

        """ Remove UID from the store.
        """


class CatalogEventQueueSet( Persistent ):

    """ Manage a set of CatalogEventQueue objects.
    """

    def __init__( self
                , delegate=None
                , bucket_count=1009
                ):

        self.setDelegate( delegate )
        self.setBucketCount( bucket_count )

    #
    #   Accessors
    #
    def getDelegate( self ):

        """ Return the callback object used to process events.
        """
        return self._delegate

    def getBucketCount( self ):

        """ How many buckets in our hashtable?
        """
        return self._bucket_count

    def listEvents( self ):

        """ Return all events we currently know about.

        o Each item in the returned sequence is a tuple, ( uid, event ).

        o This function is a generator.

        o This function does *not* drain the queues.
        """
        for queue in filter( None, self._queues ):
            for item in queue._data.items():
                uid, ( t, event ) = item
                yield uid, event


    #
    #   Mutators
    #
    def setDelegate( self, delegate ):

        """ Update our delegate.

        o If not None, 'delegate' must implement ICatalogEventQueueSetDelegate,
          else raise ValueError.
        """
        if ( delegate is not None
         and not ICatalogEventQueueSetDelegate.isImplementedBy( delegate )
           ):
            raise ValueError, "'delegate' doesn't implement ICEQSD!"

        self._delegate = delegate

    def setBucketCount( self, bucket_count ):

        """ Resize the hashtable.

        o 'bucket_count' must be a positive, prime integer, else raise
          ValueError.

        o N.B.:  If successful, we destroy any existing queues!
        """
        if ( type( bucket_count ) is not type( 0 )
            or bucket_count < 3
            or not _isPrime( bucket_count )
           ):
            raise ValueError, 'bucket_count must be a positive, prime int!'

        self._bucket_count = bucket_count
        self._clear()

    def update( self, uid, event ):

        """ Add an event to our queue.

        o 'event' must be one of the EVENT_TYPES.
        """
        if event not in EVENT_TYPES:
            raise ValueError, 'Not a known event: %s' % event

        self._queues[ hash( uid ) % self._bucket_count ].update( uid, event )

    def process( self ):

        """ Process events in the queues.
        """
        for queue in filter( None, self._queues ):
            for item in queue.process().items():

                if not self._delegate:
                    continue

                uid, ( t, event ) = item

                if event == ADDED or event == CHANGED_ADDED:
                    self._delegate.add( uid )
                elif event == CHANGED:
                    self._delegate.change( uid )
                elif event == REMOVED:
                    self._delegate.remove( uid )

    #
    #   Helper methods
    #
    def _clear( self ):

        self._queues = [ CatalogEventQueue()
                            for i in range( self._bucket_count ) ]

def _isPrime( x ):

    """ isPrime(int x) --> boolean

    isPrime(x) checks if a given number x is prime. It follows the following
    decision tree:
        if x is 1 it is a special case (ie: not prime),
        if x is either 2 or 3, it is prime,
        if x is even, it is not prime.
        if x is not one of these obvious cases:
            check if x is divisible by the numbers in the range from 3 to
            floor(sqrt(x)).

    From: http://jijo.free.net.ph/programming/python/code/prime.py
    """       
    if (x == 1):                    # Special case, neither prime nor composite
        return None
    elif ((x == 2) or (x == 3)):
        return x
    elif ((x % 2) == 0):
        return None
    else:
        flag = 0
        i = 3
        while 1:
            if (x % i) == 0:
                return 0
            elif (i * i) > x:
                return 1
            i += 2



