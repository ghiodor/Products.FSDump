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
from zLOG.tests.testzLog import StupidLogTest

# Use a module global to store a fresh Zope app *once* per test run
# This avoids having to recreate one everytime the unittest framework
# instantiates the test case anew, which it tends to do often

_conn = None

def makeConnection():
    from ZODB import DB
    from ZODB.DemoStorage import DemoStorage

    s = DemoStorage(quota=(1<<20))
    return DB( s ).open()

def getZopeApp():

    from cStringIO import StringIO
    from OFS.Application import Application
    from OFS.Application import initialize as initialize_app
    from Testing.makerequest import makerequest

    global _conn
    if _conn is None: # or fresh_db:
        _conn = makeConnection()
        try:
            root = _conn.root()
            app = Application()
            root['Application'] = app
            responseOut = StringIO()
            app = makerequest(app, stdout=responseOut)
            get_transaction().commit(1)
            initialize_app(app)
            get_transaction().commit(1)
            return app
        except:
            _conn.close()
            _conn = None
            raise
    else:
        app = _conn.root()['Application']
        responseOut = StringIO()
        return makerequest(app, stdout=responseOut)


class QueueCatalogTests(StupidLogTest):

    def setUp(self):
        app = getZopeApp()
        self.app = app
        app.real_cat = ZCatalog('real_cat')
        app.real_cat.addIndex('id', 'FieldIndex')
        app.real_cat.addIndex('title', 'FieldIndex')
        app.real_cat.addIndex('meta_type', 'FieldIndex')
        app.queue_cat = QueueCatalog(3) # 3 buckets
        app.queue_cat.id = 'queue_cat'
        app.queue_cat.manage_edit(location='/real_cat',
                                  immediate_indexes=['id', 'title'])
        StupidLogTest.setUp(self)

    def tearDown(self):
        get_transaction().abort()
        try:
            StupidLogTest.tearDown(self)
        except OSError:
            pass

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

    def testPinpointIndexes(self):
        app = self.app
        app.queue_cat.setImmediateMetadataUpdate(True)
        app.queue_cat.setProcessAllIndexes(False)
        app.f1 = Folder()
        app.f1.id = 'f1'
        app.f1.title = 'Joe'
        app.queue_cat.catalog_object(app.f1, idxs=['id'])
        # The 'id' index gets updated immediately.
        res = app.queue_cat.searchResults(id='f1')
        self.assertEqual(len(res), 1)
        res = app.queue_cat.searchResults(title='Joe')
        self.assertEqual(len(res), 1)
        # even though we requested that only 'id' and title be updated, 
        # because this is a new entry, it should still be in the queue.
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 0)
        app.queue_cat.process()
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 1)
        # Now we will change both the title and the meta_type but only ask the
        # title to be indexed
        app.f1.meta_type = 'Duck'
        app.f1.title = 'Betty'
        app.queue_cat.catalog_object(app.f1, idxs=['title'])
        res = app.queue_cat.searchResults(title='Joe')
        self.assertEqual(len(res), 0)
        res = app.queue_cat.searchResults(title='Betty')
        self.assertEqual(len(res), 1)
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 1)
        app.queue_cat.process()
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 1)
        res = app.queue_cat.searchResults(meta_type='Duck')
        self.assertEqual(len(res), 0)
        # now we will change the title again but only ask that the meta_type
        # be indexed.  All deferred indexes will index, but not title
        app.f1.title = 'Susan'
        app.queue_cat.catalog_object(app.f1, idxs=['meta_type'])
        res = app.queue_cat.searchResults(title='Betty')
        self.assertEqual(len(res), 1) # no change
        res = app.queue_cat.searchResults(meta_type='Duck')
        self.assertEqual(len(res), 0) # no change
        app.queue_cat.process()
        res = app.queue_cat.searchResults(meta_type='Duck')
        self.assertEqual(len(res), 1) # change!

    def testIndexOnce(self):
        # this behavior is important to reduce conflict errors.
        app = self.app
        app.queue_cat.setImmediateMetadataUpdate(True)
        app.queue_cat.setProcessAllIndexes(False)
        app.f1 = Folder()
        app.f1.id = 'f1'
        app.f1.title = 'Joe'
        app.queue_cat.catalog_object(app.f1)
        res = app.queue_cat.searchResults(title='Joe')
        self.assertEqual(len(res), 1)
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 0)
        app.f1.title = 'Missed me'
        app.queue_cat.process()
        res = app.queue_cat.searchResults(title='Joe')
        self.assertEqual(len(res), 1) # already indexed
        res = app.queue_cat.searchResults(meta_type='Folder')
        self.assertEqual(len(res), 1)

    def testMetadataOnce(self):
        # this behavior is important to reduce conflict errors.
        app = self.app
        app.queue_cat.setImmediateMetadataUpdate(True)
        app.queue_cat.setProcessAllIndexes(False)
        app.real_cat.addColumn('title')
        app.f1 = Folder()
        app.f1.id = 'f1'
        app.f1.title = 'Joe'
        app.queue_cat.catalog_object(app.f1) # metadata should change
        res = app.queue_cat.searchResults(id='f1')[0]
        self.assertEqual(res.title, 'Joe')
        app.f1.title = 'Betty'
        app.queue_cat.process() # metadata should not change
        res = app.queue_cat.searchResults(id='f1')[0]
        self.assertEqual(res.title, 'Joe')
        # now we'll change the policy
        app.queue_cat.setImmediateMetadataUpdate(False)
        app.queue_cat.catalog_object(app.f1) # metadata should not change
        res = app.queue_cat.searchResults(id='f1')[0]
        self.assertEqual(res.title, 'Joe')
        app.queue_cat.process() # metadata should change
        res = app.queue_cat.searchResults(id='f1')[0]
        self.assertEqual(res.title, 'Betty')

    def testLogCatalogErrors(self):
        self.setLog()
        app = self.app
        app.f1 = Folder()
        app.f1.id = 'f1'
        app.queue_cat.catalog_object(app.f1)
        app.real_cat.catalog_object = lambda : None # raises TypeError
        app.queue_cat.process()
        del app.real_cat.catalog_object
        app.queue_cat.setImmediateRemoval(False)
        app.queue_cat.uncatalog_object(app.queue_cat.uidForObject(app.f1))
        app.real_cat.uncatalog_object = lambda : None # raises TypeError
        app.queue_cat.process()
        del app.real_cat.uncatalog_object
        f = self.getLogFile()
        self.verifyEntry(f, subsys="QueueCatalog",
                         summary="error cataloging object")
        # the verify method in the log tests is broken :-(
        l = f.readline()
        marker = "------\n"
        while l != marker:
            l = f.readline()
            if not l:
                self.fail('could not find next log entry')
        f.seek(f.tell() - len(marker))
        self.verifyEntry(f, subsys="QueueCatalog",
                         summary="error uncataloging object")

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
        self.assertEqual(len(info), 3)
        self.assert_({'id': 'id', 'meta_type': 'FieldIndex'} in info)
        self.assert_({'id': 'meta_type', 'meta_type': 'FieldIndex'} in info)
        self.assert_({'id': 'title', 'meta_type': 'FieldIndex'} in info)
        
    
    def testRealCatSpecifiesUids(self):
        def stupidUidMaker(self, obj):
            return '/stupid/uid'
        ZCatalog.uidForObject = stupidUidMaker # monkey patch
        self.assertEqual(self.app.queue_cat.uidForObject(None), '/stupid/uid')

    def testImmediateDeletion(self):
        app = self.app
        app.test_cat = QueueCatalog(1000)  # 1000 buckets. I don't want collisions here.
        app.test_cat.id = 'test_cat'
        app.test_cat.manage_edit(location='/real_cat',
                                  immediate_indexes=['id'], immediate_removal=1)
        for n in range(20):
            f = Folder()
            f.id = 'f%d' % n
            setattr(app, f.id, f)
            f = getattr(app, f.id)
            app.test_cat.catalog_object(f)
        self.assertEqual(app.test_cat.manage_size(), 20)
        # "Delete" one. This should be processed immediately (including the add-event)
        app.test_cat.uncatalog_object(getattr(app, 'f1').getPhysicalPath())
        self.assertEqual(app.test_cat.manage_size(), 19)
        del app.test_cat

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

