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
"""QueueCatalog tests.

$Id$
"""

import unittest
import Testing
import Zope
Zope.startup()

from Products.ZCatalog.ZCatalog import ZCatalog
from Products.QueueCatalog.QueueCatalog import QueueCatalog
from OFS.Folder import Folder


class QueueCatalogTests(unittest.TestCase):

    def setUp(self):
        app = Zope.app()
        self.app = app
        app.real_cat = ZCatalog('real_cat')
        app.real_cat.addIndex('id', 'FieldIndex')
        app.real_cat.addIndex('meta_type', 'FieldIndex')
        app.queue_cat = QueueCatalog(3)  # 3 buckets
        app.queue_cat.id = 'queue_cat'
        app.queue_cat.manage_edit(location='/real_cat',
                                  immediate_indexes=['id'])

    def tearDown(self):
        get_transaction().abort()
        del self.app


    def testAddObject(self):
        app = self.app
        app.f1 = Folder()
        app.f1.id = 'f1'
        self.assertEqual(app.queue_cat.manage_size(), 0)
        self.assertEqual(len(app.real_cat), 0)
        app.queue_cat.catalog_object(app.f1)
        self.assertEqual(app.queue_cat.manage_size(), 1)
        self.assertEqual(len(app.real_cat), 1)


    def testDeferMostIndexes(self):
        app = self.app
        app.f1 = Folder()
        app.f1.id = 'f1'
        app.queue_cat.catalog_object(app.f1)
        # The 'id' index gets updated immediately.
        res = app.queue_cat.searchResults(id='f1')
        self.assertEqual(len(res), 1)
        # In this test, the 'meta_type' index gets updated later.
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 0)
        # Process the queue.
        app.queue_cat.process()
        # Now that the queue has been processed, the item shows up.
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 1)


    def testQueueProcessingLimit(self):
        # Don't try to process too many items at once.
        app = self.app
        for n in range(100):
            f = Folder()
            f.id = 'f%d' % n
            setattr(app, f.id, f)
            f = getattr(app, f.id)
            app.queue_cat.catalog_object(f)
        # None of the items should be in the meta_type index yet.
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 0)
        # Process only 10 of the items.
        app.queue_cat.process(max=10)
        # There should now be 10 items in the results.
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 10)
        # Process another 25.
        app.queue_cat.process(max=25)
        # There should now be 35 items in the results.
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 35)
        # Finish.
        app.queue_cat.process()
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 100)


    def testGetIndexInfo(self):
        info = self.app.queue_cat.getIndexInfo()
        self.assertEqual(len(info), 2)
        self.assert_({'id': 'id', 'meta_type': 'FieldIndex'} in info)
        self.assert_({'id': 'meta_type', 'meta_type': 'FieldIndex'} in info)
        
    
    def testRealCatSpecifiesUids(self):
        def stupidUidMaker(self, obj):
            return '/stupid/uid'
        ZCatalog.uidForObject = stupidUidMaker # monkey patch
        self.assertEqual(self.app.queue_cat.uidForObject(None), '/stupid/uid')

# Enable this test when DemoStorage supports conflict resolution.

##    def testSimpleConflict(self):
##        # Verifies that the queue resolves conflicts.
##        # Prepare the data.
##        app = self.app
##        for n in range(10):
##            f = Folder()
##            f.id = 'f%d' % n
##            setattr(app, f.id, f)
##            g = Folder()
##            g.id = 'g%d' % n
##            setattr(app, g.id, g)
##        get_transaction().commit()
##        # Queue some events.
##        for n in range(10):
##            f = getattr(app, 'f%d' % n) 
##            app.queue_cat.catalog_object(f)
##        # Let another thread add events that change the same queues.
##        from thread import start_new_thread, allocate_lock
##        lock = allocate_lock()
##        lock.acquire()
##        start_new_thread(self._simpleConflictThread, (lock,))
##        lock.acquire()
##        # Verify the other thread did its work.
##        app2 = Zope.app()
##        try:
##            self.assertEqual(len(app2.queue_cat()), 10)
##        finally:
##            del app2
##        # Commit the conflicting changes.
##        get_transaction().commit()
##        # Did it work?
##        self.assertEqual(len(app.queue_cat()), 20)

##    def _simpleConflictThread(self, lock):
##        try:
##            app = Zope.app()
##            for n in range(10):
##                g = getattr(app, 'g%d' % n) 
##                app.queue_cat.catalog_object(g)
##            get_transaction().commit()
##            del app
##        finally:
##            lock.release()


if __name__ == '__main__':
    unittest.main()

