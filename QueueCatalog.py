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

from zExceptions import Unauthorized
from ExtensionClass import Base
from OFS.SimpleItem import SimpleItem
from AccessControl.SecurityManagement import getSecurityManager
from AccessControl.SecurityInfo import ClassSecurityInformation
from OFS.SimpleItem import SimpleItem
from BTrees.OOBTree import OOBTree
from time import time
from CatalogEventQueue import CatalogEventQueue, EVENT_TYPES, ADDED_EVENTS
from CatalogEventQueue import ADDED, CHANGED, CHANGED_ADDED, REMOVED
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Globals import DTMLFile
from Acquisition import Implicit

StringType = type('')

_zcatalog_methods = {
    'catalog_object': 1,
    'uncatalog_object': 1,
    'uniqueValuesFor': 1,
    'getpath': 1,
    'getrid': 1,
    'getobject': 1,
    'schema': 1,
    'indexes': 1,
    'index_objects': 1,
    'searchResults': 1,
    '__call__': 1,
    }

_zcatalog_method = _zcatalog_methods.has_key

_views = {}

class QueueCatalog(Implicit, SimpleItem):
    """Queued ZCatalog (Proxy)

    A QueueCatalog delegates most requests to a ZCatalog that is named
    as part of the QueueCatalog configuration.

    Requests to catalog or uncatalog objects are queued. They must be
    processed by a separate process (or thread). The queuing provides
    benefits:

    - Content-management operations, performed by humans, complete
      much faster, this making the content-management system more
      effiecient for it's users.

    - Catalog updates are batched, which makes indexing much more
      efficient.

    - Indexing is performed by a single thread, allowing more
      effecient catalog document generation and avoiding conflict
      errors from occuring during indexing.

    - When used with ZEO, indexing might e performed on the same
      machine as the storage server, making updates faster.
      
    """

    def __init__(self, buckets=1009):
        self._buckets = buckets
        self._location = None
        self._queues = [CatalogEventQueue() for i in range(buckets)]

    def setLocation(self, location):
        if self._location is not None:
            try:
                self.process()
            except TypeError:
                # clear the queues
                self.__init__()

        self._location = location
        

    def getZCatalog(self, method=''):
        
        ZC = getattr(self, '_v_ZCatalog', None)
        if ZC is None:
            if self._location is None:
                raise TypeError(
                    "This QueueCatalog hasn't been "
                    "configured with a ZCatalog location."
                    )
            ZC = self.unrestrictedTraverse(self._location)
            self._v_ZCatalog = ZC

        security_manager = getSecurityManager()

        if not security_manager.validateValue(ZC):
            raise Unauthorized(self._location, ZC)

        if method:
            if not _zcatalog_method(method):
                raise AttributeError(method)
            ZC = getattr(ZC, method)
            if not security_manager.validateValue(ZC):
                raise Unauthorized(name=method)
                

        return ZC

    def __getattr__(self, name):
        # The original object must be wrapped, but self isn't, so
        # we return a special object that will do the attribute access
        # on a wrapped object. 
        if _zcatalog_method(name):
            return AttrWrapper(name)

        raise AttributeError(name)

    def _update(self, uid, etype):
        if uid[:1] != '/':
            raise TypeError("uid must start with '/'")

        t = time()
        self._queues[hash(uid) % self._buckets].update(uid, etype)
        
    def catalog_object(self, obj, uid=None):

        # Make sure the current context is allowed to to this:
        catalog_object = self.getZCatalog('catalog_object')
        
        if uid is None:
            uid = '/'.join(obj.getPhysicalPath())
        elif type(uid) is not StringType:
            uid = '/'.join(uid)

        # The ZCatalog API doesn't allow us to distinguish between
        # adds and updates, so we have to try to figure this out
        # ourselves.

        # There's a risk of a race here. What if there is a previously
        # unprocessed add event? If so, then this should be a changed
        # event. If we undo this transaction later, we'll generate a
        # remove event, when we should generate an add changed event.
        # To avoid this, we need to make sure we see consistent values
        # of the event queue. We also need to avoid resolving
        # (non-undo) conflicts of add events. This will slow things
        # down a bit, but adds should be relatively infrequent. 

        # Now, try to decide if the catalog has the uid (path).

        catalog = self.getZCatalog()

        if cataloged(catalog, uid):
            event = CHANGED
        else:
            # Looks like we should add, but maybe there's already a
            # pending add event. We'd better check the event queue:
            
            if (self._queues[hash(uid) % self._buckets].getEvent(uid) in
                ADDED_EVENTS):
                event = CHANGED
            else:
                event = ADDED
        
        self._update(uid, event)

    def uncatalog_object(self, uid):

        # Make sure the current context is allowed to to this:
        self.getZCatalog('uncatalog_object')

        if type(uid) is not StringType:
            uid = '/'.join(uid)

        self._update(uid, REMOVED)

    def process(self):
        "Process pending events"
        catalog = self.getZCatalog()
        for queue in filter(None, self._queues):
            events = queue.process()
            for uid, (t, event) in events.items():
                if event is REMOVED:
                    if cataloged(catalog, uid):
                        catalog.uncatalog_object(uid)
                else:
                    # add or change

                    if event is CHANGED and not cataloged(catalog, uid):
                        continue
                    
                    obj = self.unrestrictedTraverse(uid)
                    catalog.catalog_object(obj, uid)

    # Provide web pages. It would be nice to use views, but Zope 2.6
    # just isn't ready for views. :( In particular, we'd have to fake
    # out the PageTemplateFiles in some brittle way to make them do
    # the right thing. :(

    manage_editForm = DTMLFile('dtml/edit', globals())

    def manage_getLocation(self):
        return self._location or ''


    def manage_edit(self, title='', location='', REQUEST=None):
        """ Edit the instance """
        self.title = title
        self.setLocation(location or None)

        if REQUEST is not None:
            msg = 'Properties changed'
            return self.manage_editForm( self
                                       , REQUEST
                                       , manage_tabs_message=msg
                                       )
        
    
    manage_queue = DTMLFile('dtml/queue', globals())

    def manage_size(self):
        size = 0
        for q in self._queues:
            size += len(q)

        return size

    def manage_process(self, REQUEST):
        "Web UI to manually process queues"
        # make sure we have necessary perm
        self.getZCatalog('catalog_object')
        self.getZCatalog('uncatalog_object')
        self.process()

        msg = 'Queue processed'
        return self.manage_queue( self
                                , REQUEST
                                , manage_tabs_message=msg
                                )
    
    # Provide Zope 2 offerings

    index_html = None

    meta_type = 'ZCatalog Queue'

    __allow_access_to_unprotected_subobjects__ = 0
    manage_options=(
        (
        {'label': 'Configure', 'action': 'manage_editForm',
         'help':('QueueCatalog','QueueCatalog-Configure.stx')},

        {'label': 'Queue', 'action': 'manage_queue',
         'help':('QueueCatalog','QueueCatalog-Queue.stx')},
        )
        +SimpleItem.manage_options
        )

    security = ClassSecurityInformation()

    security.declareObjectPublic()

    security.declarePublic('catalog_object', 'uncatalog_object',
                           'manage_process')

    security.declareProtected(
        'View management screens',
        'manage_editForm', 'manage_edit',
        'manage_queue', 'manage_getLocation',
        'manage_size'
        )
    
def cataloged(catalog, path):
    getrid = getattr(catalog, 'getrid', None)
    if getrid is None:
        
        # This is an old catalog that doesn't provide an API for
        # getting an objects rid (and thus determing that the
        # object is already cataloged.
        
        # We'll just use our knowledge of the internal structure.
        
        rid = catalog._catalog.uids.get(path)
        
    else:
        rid = catalog.getrid(path)

    return rid is not None

class AttrWrapper(Base):
    "Special object that allowes us to use acquisition in QueueCatalog "
    "attribute access"

    def __init__(self, name):
        self.__name__ = name

    def __of__(self, wrappedQueueCatalog):
        return wrappedQueueCatalog.getZCatalog(self.__name__)

__doc__ = QueueCatalog.__doc__ + __doc__







