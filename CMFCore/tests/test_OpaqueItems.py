from unittest import TestCase, TestSuite, makeSuite, main
from types import StringType

import Zope
try:
    Zope.startup()
except AttributeError:
    # for Zope versions before 2.6.1
    pass
try:
    from Interface.Verify import verifyClass
except ImportError:
    # for Zope versions before 2.6.0
    from Interface import verify_class_implementation as verifyClass

from Products.CMFCore.TypesTool import TypesTool
from Products.CMFCore.PortalFolder import PortalFolder

from Products.CMFCore.tests.base.testcase import SecurityTest
from Products.CMFCore.tests.base.dummy import DummyContent as OriginalDummyContent

from Products.CMFCore.interfaces.IOpaqueItems import ICallableOpaqueItemWithHooks


# -------------------------------------------
# Helper classes and functions
# -------------------------------------------

def extra_meta_types():
    return [{'name': 'Dummy', 'action': 'manage_addFolder'}]

def addDummyContent(container, id, opaqueItem):
    container._setObject(id, DummyContent(id, opaqueItem=opaqueItem, catalog=1))
    return getattr(container, id)

class DummyContent(OriginalDummyContent):
    """ A Dummy piece of PortalContent with additional attributes
    """
    
    def __init__(self, id='dummy', opaqueItem=None, *args, **kw ):
        apply(OriginalDummyContent.__init__, (self, id) + args, kw)
        if opaqueItem is None:
            self.opaqueItem = 'noncallable'
            self.opaqueItemsId = 'opaqueItem'
        elif type(opaqueItem) is StringType:
            setattr(self, opaqueItem, HooksOnly(opaqueItem))
            self.opaqueItemsId = opaqueItem
        else:
            self.opaqueItem = opaqueItem('opaqueItem')
            self.opaqueItemsId = 'opaqueItem'
        
    # Ensure additional attributes get copied
    def _getCopy(self, container):
        obj = DummyContent(self.id, catalog=self.catalog)
        setattr(obj, self.opaqueItemsId, getattr(self, self.opaqueItemsId))
        return obj
        
    def isNotifiedByAfterAdd(self):
        return getattr(getattr(self, self.opaqueItemsId), 'addCount', None)
    
    def isNotifiedByAfterClone(self):
        return getattr(getattr(self, self.opaqueItemsId), 'cloneCount', None)
    
    def isNotifiedByBeforeDelete(self):
        return getattr(getattr(self, self.opaqueItemsId), 'deleteCount', None)
    
class OpaqueBase:
    """ Opaque item without manage_after/before hookes
    """
    def __init__(self, id):
        self.id = id
        self.addCount = self.cloneCount = self.deleteCount = 0
        self.addCounter = self.cloneCounter = self.deleteCounter = 1

class MarkerOnly(OpaqueBase):
    """ Opaque item without manage_after/before hookes but marked 
    as callable
    """
    __implements__ = (
        ICallableOpaqueItemWithHooks,
    )

class HooksOnly(OpaqueBase):
    """ Opaque item with manage_after/before hookes but not marked 
    as callable
    """
    def manage_afterAdd(self, item, container):
        self.addCount = self.addCounter
        self.addCounter += 1
    
    def manage_afterClone(self, item):
        self.cloneCount = self.cloneCounter
        self.cloneCounter += 1
    
    def manage_beforeDelete(self, item, container):
        self.deleteCount = self.deleteCounter
        self.deleteCounter += 1
    
class HooksAndMarker(HooksOnly, MarkerOnly):
    """ Opaque item with manage_after/before hookes and marked
    as callable
    """
    pass


# -------------------------------------------
# Unit Tests
# -------------------------------------------

class ManageBeforeAfterTests(SecurityTest):

    def setUp(self):
        SecurityTest.setUp(self)
        
        root = self.root
        
        # setting up types tool
        root._setObject( 'portal_types', TypesTool() )
        
        # setup portal
        try: root._delObject('test')
        except AttributeError: pass
        root._setObject('test', PortalFolder('test', ''))
        self.test = test = self.root.test

        # setting up folders
        test._setObject( 'folder', PortalFolder( 'folder', '' ) )
        folder = self.folder = test.folder
        folder._setObject( 'sub', PortalFolder( 'sub', '' ) )
        sub = self.sub = folder.sub
        
        #----- hacks to allow pasting (see also test_PortalFolder)
        # WAAA! force sub to allow paste of Dummy object.
        sub.all_meta_types = extra_meta_types()
        
        # delete items if necessary
        try: folder._delObject('dummy')
        except AttributeError: pass
        try: sub._delObject('dummy')
        except AttributeError: pass
        
    def test_nonCallableItem(self):
        # no exception should be raised
        folder = self.folder
        sub = self.sub
        dummy = addDummyContent(folder, 'dummy', None)
        
        # WAAAA! must get _p_jar set
        old, dummy._p_jar = sub._p_jar, self.root._p_jar
        try:
            cp = folder.manage_copyObjects(ids=['dummy'])
            sub.manage_pasteObjects(cp)
        finally:
            dummy._p_jar = old

    def test_callableItemWithMarkerOnly(self):
        folder = self.folder
        sub = self.sub
        dummy = addDummyContent(folder, 'dummy', MarkerOnly)
        
        self.failIf(dummy.isNotifiedByAfterAdd())
        self.failIf(dummy.isNotifiedByAfterClone())
        self.failIf(dummy.isNotifiedByBeforeDelete())
        
        # WAAAA! must get _p_jar set
        old, dummy._p_jar = sub._p_jar, self.root._p_jar
        try:
            cp = folder.manage_copyObjects(ids=['dummy'])
            sub.manage_pasteObjects(cp)
        finally:
            dummy._p_jar = old
        
        self.failIf(dummy.isNotifiedByAfterAdd())
        self.failIf(dummy.isNotifiedByAfterClone())
        self.failIf(dummy.isNotifiedByBeforeDelete())
        
    def test_callableItemWithHooksOnly(self):
        folder = self.folder
        sub = self.sub
        dummy = addDummyContent(folder, 'dummy', HooksOnly)
        
        self.failIf(dummy.isNotifiedByAfterAdd())
        self.failIf(dummy.isNotifiedByAfterClone())
        self.failIf(dummy.isNotifiedByBeforeDelete())
        
        # WAAAA! must get _p_jar set
        old, dummy._p_jar = sub._p_jar, self.root._p_jar
        try:
            cp = folder.manage_copyObjects(ids=['dummy'])
            sub.manage_pasteObjects(cp)
        finally:
            dummy._p_jar = old
        
        self.failIf(dummy.isNotifiedByAfterAdd())
        self.failIf(dummy.isNotifiedByAfterClone())
        self.failIf(dummy.isNotifiedByBeforeDelete())
        
    def test_callableItemWithHooksAndMarker(self):
        folder = self.folder
        sub = self.sub
        dummy = addDummyContent(folder, 'dummy', HooksAndMarker)
        
        self.assertEqual(dummy.isNotifiedByAfterAdd(), 1)
        self.failIf(dummy.isNotifiedByAfterClone())
        self.failIf(dummy.isNotifiedByBeforeDelete())
        
        # WAAAA! must get _p_jar set
        old, dummy._p_jar = sub._p_jar, self.root._p_jar
        try:
            cp = folder.manage_copyObjects(ids=['dummy'])
            sub.manage_pasteObjects(cp)
        finally:
            dummy._p_jar = old
        
        self.assertEqual(dummy.isNotifiedByAfterAdd(), 2)
        self.assertEqual(dummy.isNotifiedByAfterClone(), 1)
        self.failIf(dummy.isNotifiedByBeforeDelete())
        
    def test_talkbackItem(self):
        folder = self.folder
        sub = self.sub
        
        dummy = addDummyContent(folder, 'dummy', 'talkback')
        
        self.assertEqual(dummy.isNotifiedByAfterAdd(), 1)
        self.failIf(dummy.isNotifiedByAfterClone())
        self.failIf(dummy.isNotifiedByBeforeDelete())
        
        # WAAAA! must get _p_jar set
        old, dummy._p_jar = sub._p_jar, self.root._p_jar
        try:
            cp = folder.manage_copyObjects(ids=['dummy'])
            sub.manage_pasteObjects(cp)
        finally:
            dummy._p_jar = old
        
        self.assertEqual(dummy.isNotifiedByAfterAdd(), 2)
        self.assertEqual(dummy.isNotifiedByAfterClone(), 1)
        self.failIf(dummy.isNotifiedByBeforeDelete())
        
def test_suite():
    return TestSuite((
        makeSuite(ManageBeforeAfterTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')