##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
# All Rights Reserved.
# 
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
# 
##############################################################################
"""
$Id$
"""

from Persistence import Persistent
from ZODB.POSException import ConflictError
from time import time as current_wall_time

REMOVED       = 0
ADDED         = 1
CHANGED       = 2
CHANGED_ADDED = 3
EVENT_TYPES = (REMOVED, CHANGED, ADDED, CHANGED_ADDED)
antiEvent = {REMOVED:       ADDED,
             ADDED:         REMOVED,
             CHANGED:       CHANGED,
             CHANGED_ADDED: CHANGED_ADDED,
             }.get

ADDED_EVENTS = (CHANGED, ADDED, CHANGED_ADDED)


class CatalogEventQueue(Persistent):
    """Event queue for catalog events

    This is a rather odd queue. It organizes events by object, where
    objects are identified by uids, which happen to be string paths.

    One way that this queue is extremely odd is that it really only
    keeps track of the last event for an object. This is because we
    really only *care* about the last event for an object.

    There are three types of events:

    ADDED         -- An object was added to the catalog

    CHANGED       -- An object was changed

    REMOVED       -- An object was removed from the catalog

    CHANGED_ADDED -- Add object was added and subsequently changed.
                     This event is a consequence of the queue implementation.
                     
    Note that, although we only keep track of the most recent
    event. there are rules for how the most recent event can be
    updated:

    - It is illegal to update an ADDED, CHANGED, or CHANGED_ADDED
      event with an ADDED event or

    - to update a REMOVED event with a CHANGED event.

    We have a problem because applications don't really indicate
    whether they are are adding, or just updating.  We deduce add
    events by examining the catalog and event queue states.

    Also note that, when events are applied to the catalog, events may
    have no effect.

    - If an object is in the catalog, ADDED events are equivalent to
      CHANGED events.

    - If an object is not in the catalog, REMOVED and CHANGED events
      have no effect.

    If we undo a transaction, we generate an anti-event. The anti
    event of ADDED id REMOVED, of REMOVED is ADDED, and of CHANGED is
    CHANGED. 

    Note that these rules represent heuristics that attempt to provide
    efficient and sensible behavior for most cases. They are not "correct" in
    that they handle cases that may not seem handleable. For example,
    consider a sequence of transactions:

      T1 adds an object
      T2 removes the object
      T3 adds the object
      T4 processes the queue
      T5 undoes T1

    It's not clear what should be done in this case? We decide to
    generate a remove event, even though a later transaction added the
    object again. Is this correct? It's hard to say. The decision we
    make is not horrible and it allows us to provide a very effeicient
    implementation.  See the unit tests for other scenarious. Feel
    free to think of cases for which our decisions are unacceptably
    wrong and write unit tests for these cases.

    There are two kinds of transactions that affect the queue:

    - Application transactions always add or modify events. They never
      remove events.

    - Queue processing transactions always remove events.
    
    """

    def __init__(self):

        # Mapping from uid -> (generation, event type)
        self._data = {}

    def __nonzero__(self):
        return not not self._data

    def __len__(self):
        return len(self._data)
        
    def update(self, uid, etype):
        assert etype in EVENT_TYPES
        data = self._data
        current = data.get(uid)
        if current is not None:
            generation, current = current
            if current in ADDED_EVENTS and etype is ADDED:
                raise TypeError("Attempt to add an object that is already "
                                "in the catalog")
            if current is REMOVED and etype is CHANGED:
                raise TypeError("Attempt to change an object that has "
                                "been removed")

            if ((current is ADDED or current is CHANGED_ADDED)
                and etype is CHANGED):
                etype = CHANGED_ADDED
                
        else:
            generation = 0

        data[uid] = generation+1, etype

        self._p_changed = 1

    def getEvent(self, uid):
        state = self._data.get(uid)
        if state is not None:
            state = state[1]
        return state

    def process(self, limit=None):
        """Removes and returns events from this queue.

        If limit is specified, at most (limit) events are removed.
        """
        data = self._data
        if not limit or len(data) <= limit:
            self._data = {}
            return data
        else:
            self._p_changed = 1
            res = {}
            keys = data.keys()[:limit]
            for key in keys:
                res[key] = data[key]
                del data[key]
            return res

    def _p_resolveConflict(self, oldstate, committed, newstate):
        # Apply the changes made in going from old to newstate to
        # committed

        # Note that in the case of undo, the olddata is the data for
        # the transaction being undone and newdata is the data for the
        # transaction previous to the undone transaction.

        # Committed is always the currently committed data.

        oldstate_data  =  oldstate['_data']
        committed_data = committed['_data']
        newstate_data  =  newstate['_data']

        # Merge newstate changes into committed
        for uid, new in newstate_data.items():

            # Decide if this is a change
            old = oldstate_data.get(uid)
            
            if new != old:
                # something changed

                if old is not None:
                    # got a repeat event
                    if new[0] < old[0]:
                        # This was an undo, so give the event the undo
                        # time and convert to an anti event of the old
                        # (undone) event. 
                        new = (0, antiEvent(old[1]))
                    elif new[1] is ADDED:
                        raise ConflictError

                    # remove this event from old, so that we don't
                    # mess with it later.
                    del oldstate_data[uid]

                # Check aqainst current value. Either we want a
                # different event, in which case we give up, or we
                # do nothing.
                
                
                current = committed_data.get(uid)
                if current is not None:
                    if current[1] != new[1]:
                        # This is too complicated, bail
                        raise ConflictError
                    # nothing to do
                    continue

                committed_data[uid] = new

        # Now handler remaining events in old that weren't in new.
        # These *must* be undone events!
        for uid, old in oldstate_data.items():
            new = (0, antiEvent(old[1]))
            
            # See above
            current = committed_data.get(uid)
            if current is not None:
                if current[1] != new[1]:
                    # This is too complicated, bail
                    raise ConflictError
                # nothing to do
                continue

            committed_data[uid] = new

        return {'_data': committed_data}

__doc__ = CatalogEventQueue.__doc__ + __doc__



# Old worries

# We have a problem. We have to make sure that we don't lose too
# much history to undo, but we don't want to retain the entire
# history. We certainly don't want to execute the entire history
# when we execute a trans.
#
# Baah, no worry, if we undo in a series of unprocessed events, we
# simply restore the old event, which we have in the old state.


