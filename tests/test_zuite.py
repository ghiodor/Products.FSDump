""" Unit tests for 'zuite' module.

$Id$
"""
import unittest

try:
    import Zope2
except ImportError:
    # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()
try:
    import transaction
except ImportError:
    # BBB: for Zope 2.7
    class BBBTransaction:

        def begin(self):
            get_transaction().begin()

        def commit(self, sub=False):
            get_transaction().commit(sub)

        def abort(self, sub=False):
            get_transaction().abort(sub)

    transaction = BBBTransaction()

class DummyResponse:

    def __init__( self ):
        self._headers = {}
        self._body = None

    def setHeader( self, key, value ):
        self._headers[ key ] = value

    def write( self, body ):
        self._body = body

class ZuiteTests( unittest.TestCase ):

    _OLD_NOW = _MARKER = object()

    def setUp( self ):
        from Testing.makerequest import makerequest
        self.connection = Zope2.DB.open()
        self.root =  self.connection.root()[ 'Application' ]
        transaction.begin()
        root = self.root = makerequest( self.root )

    def tearDown( self ):

        if self._OLD_NOW is not self._MARKER:
            self._setNow( self._OLD_NOW )

        transaction.abort()
        self.connection.close()

    def _getTargetClass( self ):

        from Products.Zelenium.zuite import Zuite
        return Zuite

    def _makeOne( self, id='testing', *args, **kw ):

        return self._getTargetClass()( id=id, *args, **kw )

    def _setNow( self, value ):

        from DateTime.DateTime import DateTime
        from Products.Zelenium import zuite

        if isinstance( value, str ):
            value = DateTime( value )

        old, zuite._NOW = zuite._NOW, value
        return old

    def _verifyArchive( self, bits, contents ):
        import StringIO
        import zipfile
        stream = StringIO.StringIO( bits )
        archive = zipfile.ZipFile( stream, 'r' )

        names = list( archive.namelist() )
        names.sort()
        contents = list( contents )
        contents.sort()

        self.assertEqual( len( contents ), len( names ),
                          "\n==========\n%s\n==========\n%s\n==========\n"
                            % ( '\n'.join( contents )
                              , '\n'.join( names )
                              )
                        )

        for name in names:
            if name not in contents:
                raise AssertionError, 'Extra name in archive: %s' % name

        for name in contents:
            if name not in names:
                raise AssertionError, 'Missing name in archive: %s' % name

    def _verifyManifest( self, bits, name, contents ):

        import StringIO
        import zipfile
        stream = StringIO.StringIO( bits )
        archive = zipfile.ZipFile( stream, 'r' )

        manifest = filter( None, archive.read( name ).split( '\n' ) )
        self.assertEqual( len( manifest ), len( contents ) )

        for lhs, rhs in zip( manifest, contents ):
            self.assertEqual( lhs, rhs )

    def _listDefaultArchiveNames( self ):

        from Products.Zelenium.zuite import _SUPPORT_FILES

        expected_names = _SUPPORT_FILES.keys()
        expected_names.append( 'index.html' )
        expected_names.append( 'testSuite.html' )

        return expected_names

    def _makeFile( self, id, title=None, file=None ):

        from OFS.Image import File

        if title is None:
            title = 'File %s' % id

        if file is None:
            file = ''

        return File( id, title, file )

    def test_empty( self ):

        zuite = self._makeOne()
        self.assertEqual( len( zuite.test_case_metatypes ), 2 )
        self.failUnless( 'File' in zuite.test_case_metatypes )
        self.failUnless( 'Page Template' in zuite.test_case_metatypes )
        self.assertEqual( len( zuite.listTestCases() ), 0 )

    def test___getitem___normal( self ):

        from Acquisition import aq_base

        _KEY = 'key'
        zuite = self._makeOne()

        try:
            object = zuite[ _KEY ]
        except KeyError:
            pass
        else:
            self.fail( "__getitem__ didn't raise: %s" % _KEY )

        zuite._setObject( _KEY, self._makeFile( _KEY ) )
        object = zuite[ _KEY ]
        self.failUnless( aq_base( object )
                      is aq_base( getattr( zuite, _KEY ) ) )

    def test___getitem___support_files( self ):

        from Products.Zelenium.zuite import _SUPPORT_FILE_NAMES

        zuite = self._makeOne()

        for name in _SUPPORT_FILE_NAMES:
            object = zuite[ name ]
            self.assertEqual( object.meta_type, 'File' )

    def test___getitem___filesystem( self ):

        import os
        from Globals import package_home

        zuite = self._makeOne()
        zuite._updateProperty( 'filesystem_path'
                             , os.path.join( package_home( globals() )
                                           , 'flat'
                                           )
                             )

        for name in ( 'test_simple.html'
                    ,
                    ):
            object = zuite[ name ]
            self.assertEqual( object.meta_type, 'File' )

    def test___getitem___filesystem_recursive( self ):

        import os
        from Globals import package_home

        zuite = self._makeOne()
        zuite._updateProperty( 'filesystem_path'
                             , os.path.join( package_home( globals() )
                                           , 'nested'
                                           )
                             )

        for subdir, name in ( ( 'one', 'test_one.html' )
                            , ( 'two', 'test_another.html' )
                            ):
            proxy = zuite[ subdir ]
            object = proxy[ name ]
            self.assertEqual( object.meta_type, 'File' )

    def test___getitem___filesystem_filtered( self ):

        import os
        from Globals import package_home

        zuite = self._makeOne()
        zuite._updateProperty( 'filesystem_path'
                             , os.path.join( package_home( globals() )
                                           , 'filters'
                                           )
                             )

        zuite._updateProperty( 'filename_glob'
                             , 'test_*.html'
                             )

        try:
            excluded = zuite[ 'exclude_me.html' ]
        except KeyError:
            pass
        else:
            self.fail( "Didn't exclude 'exclude_me.html'." )

        for name in ( 'test_one.html'
                    , 'test_another.html'
                    ):
            object = zuite[ name ]
            self.assertEqual( object.meta_type, 'File' )

    def test_listTestCases_simple( self ):

        _TEST_IDS = ( 'test_one'
                    , 'test_two'
                    , 'test_three'
                    )

        zuite = self._makeOne()

        for test_id in _TEST_IDS:
            zuite._setObject( test_id, self._makeFile( test_id ) )

        cases = zuite.listTestCases()
        self.assertEqual( len( cases ), len( _TEST_IDS ) )
        for case in cases:
            self.failUnless( case[ 'id' ] in _TEST_IDS )

        zuite.test_case_metatypes = ()
        self.assertEqual( len( zuite.listTestCases() ), 0 )

        zuite.test_case_metatypes = ( 'File', )
        cases = zuite.listTestCases()
        self.assertEqual( len( cases ), len( _TEST_IDS ) )
        for case in cases:
            self.failUnless( case[ 'id' ] in _TEST_IDS )

    def test_listTestCases_recursive( self ):

        _TEST_IDS = ( 'test_one'
                    , 'test_two'
                    , 'test_three'
                    )

        _SUB_IDS = tuple( [ x + '_sub' for x in _TEST_IDS[:-1] ] )

        # Create a zuite inside a zuite, each populated with testcases.
        zuite = self._makeOne()

        for test_id in _TEST_IDS:
            zuite._setObject( test_id, self._makeFile( test_id ) )

        sub = self._makeOne()

        for sub_id in _SUB_IDS:
            sub._setObject( sub_id, self._makeFile( sub_id ) )

        zuite._setObject( 'sub', sub )

        # verify that the default settings pick up all tests.
        cases = zuite.listTestCases()
        expected = _TEST_IDS + _SUB_IDS
        self.assertEqual( len( cases ), len( expected ) )
        for case in cases:
            self.failUnless( case[ 'id' ] in expected )

        # verfiy that disabling the parent's metatypes leaves the child's OK.
        zuite.test_case_metatypes = ()
        cases = zuite.listTestCases()
        self.assertEqual( len( cases ), len( _SUB_IDS ) )
        for case in cases:
            self.failUnless( case[ 'id' ] in _SUB_IDS )

        # verfiy that disabling the child's metatypes leaves the parent's OK.
        zuite.test_case_metatypes = ( 'File', )
        sub.test_case_metatypes = ()
        cases = zuite.listTestCases()
        self.assertEqual( len( cases ), len( _TEST_IDS ) )
        for case in cases:
            self.failUnless( case[ 'id' ] in _TEST_IDS )

    def test_listTestCases_filesystem( self ):

        import os
        from Globals import package_home

        zuite = self._makeOne()
        zuite._updateProperty( 'filesystem_path'
                             , os.path.join( package_home( globals() )
                                           , 'flat'
                                           )
                             )

        cases = zuite.listTestCases()
        self.assertEqual( len( cases ), 1 )
        self.assertEqual( cases[ 0 ][ 'id' ], 'test_simple.html' )

    def test_listTestCases_filesystem_recursive( self ):

        import os
        from Globals import package_home

        zuite = self._makeOne()
        zuite._updateProperty( 'filesystem_path'
                             , os.path.join( package_home( globals() )
                                           , 'nested'
                                           )
                             )

        cases = zuite.listTestCases()
        self.assertEqual( len( cases ), 2 )
        case_ids = [ x[ 'id' ] for x in cases ]
        self.failUnless( 'test_one.html' in case_ids )
        self.failUnless( 'test_another.html' in case_ids )

    def test_listTestCases_filesystem_ordered_default( self ):

        # By default, sort alphabetically.
        import os
        from Globals import package_home

        zuite = self._makeOne()
        zuite._updateProperty( 'filesystem_path'
                             , os.path.join( package_home( globals() )
                                           , 'ordered'
                                           , 'default'
                                           )
                             )
        cases = zuite.listTestCases()
        self.assertEqual( len( cases ), 2 )
        case_ids = [ x[ 'id' ] for x in cases ]
        self.assertEqual( case_ids[ 0 ], 'test_alpha.html' )
        self.assertEqual( case_ids[ 1 ], 'test_beta.html' )

    def test_listTestCases_filesystem_ordered_explicit( self ):

        # Use the ordering specified in '.objects'.
        import os
        from Globals import package_home

        zuite = self._makeOne()
        zuite._updateProperty( 'filesystem_path'
                             , os.path.join( package_home( globals() )
                                           , 'ordered'
                                           , 'explicit'
                                           )
                             )
        cases = zuite.listTestCases()
        self.assertEqual( len( cases ), 2 )
        case_ids = [ x[ 'id' ] for x in cases ]
        self.assertEqual( case_ids[ 0 ], 'test_beta.html' )
        self.assertEqual( case_ids[ 1 ], 'test_alpha.html' )

    def test_listTestCases_filesystem_recursive_explicit( self ):

        import os
        from Globals import package_home

        zuite = self._makeOne()
        zuite._updateProperty( 'filesystem_path'
                             , os.path.join( package_home( globals() )
                                           , 'fussy'
                                           )
                             )
        cases = zuite.listTestCases()
        case_ids = [ x[ 'id' ] for x in cases ]
        self.assertEqual( len( case_ids ), 5, case_ids )
        self.assertEqual( case_ids[ 0 ], 'test_niece1.html' )
        self.assertEqual( case_ids[ 1 ], 'test_niece2.html' )
        self.assertEqual( case_ids[ 2 ], 'test_uncle.html' )
        self.assertEqual( case_ids[ 3 ], 'test_nephew2.html' )
        self.assertEqual( case_ids[ 4 ], 'test_nephew1.html' )

    def test_getZipFileName( self ):

        _ID = 'gzf'
        _NOW = '2005-05-02'
        self._OLD_NOW = self._setNow( _NOW )

        zuite = self._makeOne( _ID )
        self.assertEqual( zuite.getZipFileName()
                        , '%s-%s.zip' % ( _ID, _NOW ) )

    def test_manage_getZipFile_empty( self ):

        _ID = 'mgzf_empty'
        _ARCHIVE_NAME = 'empty.zip'

        response = DummyResponse()
        zuite = self._makeOne( _ID ).__of__( self.root )

        zuite.manage_getZipFile( archive_name=_ARCHIVE_NAME, RESPONSE=response )

        self.assertEqual( response._headers[ 'Content-type' ]
                        , 'application/zip' )
        self.assertEqual( response._headers[ 'Content-disposition' ]
                        , 'inline;filename=%s' % _ARCHIVE_NAME )
        self.assertEqual( response._headers[ 'Content-length' ]
                        , str( len( response._body ) ) )

        expected = self._listDefaultArchiveNames()
        expected.append( '.objects' )
        self._verifyArchive( response._body, expected )
        self._verifyManifest( response._body, '.objects', [] )

    def test_manage_getZipFile_default_name( self ):

        _ID = 'mgzf'
        _NOW = '2005-05-02'
        _FILENAME = 'test_one'

        self._OLD_NOW = self._setNow( _NOW )

        response = DummyResponse()
        zuite = self._makeOne( _ID ).__of__( self.root )
        zuite._setObject( _FILENAME, self._makeFile( _FILENAME ) )

        zuite.manage_getZipFile( RESPONSE=response )

        self.assertEqual( response._headers[ 'Content-type' ]
                        , 'application/zip' )
        self.assertEqual( response._headers[ 'Content-disposition' ]
                        , 'inline;filename=%s-%s.zip' % ( _ID, _NOW ) )
        self.assertEqual( response._headers[ 'Content-length' ]
                        , str( len( response._body ) ) )

        expected = self._listDefaultArchiveNames()
        expected.append( '.objects' )
        filename = '%s.html' % _FILENAME
        expected.append( filename )
        self._verifyArchive( response._body, expected )
        self._verifyManifest( response._body, '.objects', [ filename ] )

    def test_manage_getZipFile_recursive( self ):

        _ID = 'mgzf_recursive'
        _ARCHIVE_NAME = 'recursive.zip'

        _TEST_IDS = ( 'test_one'
                    , 'test_two'
                    , 'test_three'
                    )

        _SUB_IDS = tuple( [ x + '_sub' for x in _TEST_IDS[:-1] ] )

        response = DummyResponse()
        zuite = self._makeOne( _ID ).__of__( self.root )

        for test_id in _TEST_IDS:
            zuite._setObject( test_id, self._makeFile( test_id ) )

        sub = self._makeOne()

        for sub_id in _SUB_IDS:
            sub._setObject( sub_id, self._makeFile( sub_id ) )

        zuite._setObject( 'sub', sub )

        zuite.manage_getZipFile( archive_name=_ARCHIVE_NAME, RESPONSE=response )

        self.assertEqual( response._headers[ 'Content-type' ]
                        , 'application/zip' )
        self.assertEqual( response._headers[ 'Content-disposition' ]
                        , 'inline;filename=%s' % _ARCHIVE_NAME )
        self.assertEqual( response._headers[ 'Content-length' ]
                        , str( len( response._body ) ) )

        expected = self._listDefaultArchiveNames()
        expected.append( '.objects' )
        expected.append( 'sub/.objects' )

        top_level = []
        for test_id in _TEST_IDS:
            filename = '%s.html' % test_id 
            expected.append( filename )
            top_level.append( filename )

        top_level.append( 'sub' )

        sub_level = []
        for sub_id in _SUB_IDS:
            filename = '%s.html' % sub_id
            expected.append( 'sub/%s' % filename )
            sub_level.append( filename )

        self._verifyArchive( response._body, expected )
        self._verifyManifest( response._body, '.objects', top_level )
        self._verifyManifest( response._body, 'sub/.objects', sub_level )

    def test_manage_createSnapshot_empty( self ):

        _ID = 'mcs_empty'
        _ARCHIVE_NAME = 'empty.zip'
        zuite = self._makeOne( _ID ).__of__( self.root )

        zuite.manage_createSnapshot( archive_name=_ARCHIVE_NAME )
        object_ids = zuite.objectIds()
        self.assertEqual( len( object_ids ), 1 )
        self.failUnless( _ARCHIVE_NAME in object_ids )

        archive = zuite._getOb( _ARCHIVE_NAME )
        expected = self._listDefaultArchiveNames()
        expected.append( '.objects' )
        self._verifyArchive( archive.data, expected )

    def test_manage_createSnapshot_default_name( self ):

        _ID = 'mcs'
        _NOW = '2005-05-02'
        _FILENAME = 'test_one'

        self._OLD_NOW = self._setNow( _NOW )

        zuite = self._makeOne( _ID ).__of__( self.root )
        zuite._setObject( _FILENAME, self._makeFile( _FILENAME ) )

        zuite.manage_createSnapshot()

        object_ids = zuite.objectIds()
        self.assertEqual( len( object_ids ), 2 )
        expected_id = '%s-%s.zip' % ( zuite.getId(), _NOW )
        self.failUnless( expected_id in object_ids )

        expected = self._listDefaultArchiveNames()
        expected.append( '.objects' )
        expected.append( '%s.html' % _FILENAME )
        archive = zuite._getOb( expected_id )
        self._verifyArchive( archive.data, expected )

    def test_manage_createSnapshot_recursive( self ):

        _ID = 'mgzf_recursive'
        _ARCHIVE_NAME = 'recursive.zip'

        _TEST_IDS = ( 'test_one'
                    , 'test_two'
                    , 'test_three'
                    )

        _SUB_IDS = tuple( [ x + '_sub' for x in _TEST_IDS[:-1] ] )

        zuite = self._makeOne( _ID ).__of__( self.root )

        for test_id in _TEST_IDS:
            zuite._setObject( test_id, self._makeFile( test_id ) )

        sub = self._makeOne()

        for sub_id in _SUB_IDS:
            sub._setObject( sub_id, self._makeFile( sub_id ) )

        zuite._setObject( 'sub', sub )

        zuite.manage_createSnapshot( archive_name=_ARCHIVE_NAME )
        object_ids = zuite.objectIds()
        self.assertEqual( len( object_ids ), len( _TEST_IDS ) + 2 )
        self.failUnless( _ARCHIVE_NAME in object_ids )

        archive = zuite._getOb( _ARCHIVE_NAME )
        expected = self._listDefaultArchiveNames()
        expected.append( '.objects' )
        expected.append( 'sub/.objects' )

        for test_id in _TEST_IDS:
            expected.append( '%s.html' % test_id )

        for sub_id in _SUB_IDS:
            expected.append( 'sub/%s.html' % sub_id )

        self._verifyArchive( archive.data, expected )

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( ZuiteTests ),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
