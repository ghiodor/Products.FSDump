""" Classes: Dumper

$Id$
"""

import os
import sys

from AccessControl.class_init import InitializeClass
from AccessControl.SecurityInfo import ClassSecurityInfo
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from ZODB.POSException import ConflictError

# imports required for the loading of objects
from OFS.Folder import Folder
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.ZSQLMethods.SQL import SQL
from Products.PythonScripts.PythonScript import PythonScript
from OFS.Image import File, Image

USE_DUMPER_PERMISSION = 'Use Dumper'

# cannot use a decorator as follows because context (given by zope
# to initialize) is not available in Dumper.py
#def zope(zclass, addform, addaction, permission, icon):
#    InitializeClass(zclass)
#    context.registerClass(zclass,
#                           constructors= (addform,
#                                          addaction),
#                           permission= permission,
#                           icon=icon
#    )

manage_addFSDumpForm = PageTemplateFile('www/addDumper', globals() )

def manage_addFSDump(self, id, fspath=None, use_metadata_file=0, REQUEST=None):
    """Add a Dumper object to the system
    """
    dumper = Dumper()
    dumper.id = id
    dumper.edit(fspath, use_metadata_file)
    self._setObject(id, dumper)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect('manage_main')


def initialize(context):
    """function expected by zope at package level to register the product
       (to be imported at package level in __init__.py)
       (see Zope/OFS/Application.py)
       This approach is used, instead of the common practice to define it
       __init__.py, because it doesn't make sense to separate the definition
       of the constructors from its use (one time use), thus applying
       the principle of proximity.
    """
    InitializeClass(Dumper)
    context.registerClass(Dumper,
                          constructors= (manage_addFSDumpForm,
                                         manage_addFSDump),
                          permission= 'Add Dumper',
                          icon='www/dumper.gif'
    )

#permission= 'Add Dumper',
#icon='www/dumper.gif'
#@zope(manage_addFSDumpForm, manage_addFSDump, permission, icon)
class Dumper(SimpleItem):
    """
    """
    meta_type = 'Dumper'

    manage_options = ( { 'label'    : 'Edit'
                       , 'action'   : 'editForm'
                       , 'help'     : ('FSDump' ,'Dumper_editForm.stx')
                       }
                     , { 'label'    : 'Security'
                       , 'action'   : 'manage_access'
                       , 'help'     : ('OFSP','Security_Define-Permissions.stx')
                       }
                     )

    security = ClassSecurityInfo()
    
    fspath = None
    use_metadata_file = 0

    #
    #   Management interface methods.
    #
    index_html = None

    security.declareProtected(USE_DUMPER_PERMISSION, 'editForm')
    editForm = PageTemplateFile('www/editDumper', globals())


    @security.protected(USE_DUMPER_PERMISSION)
    def edit(self, fspath, use_metadata_file, REQUEST=None):
        """
            Update the path to which we will dump our peers.
        """
        self._setFSPath(fspath)
        self.use_metadata_file = use_metadata_file

        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(
                  self.absolute_url()
                + '/editForm'
                + '?manage_tabs_message=Dumper+updated.'
                                        )

    @security.protected(USE_DUMPER_PERMISSION)
    def dumpToFS(self, REQUEST=None):
        """
            Iterate recursively over our peers, creating simulacra
            of them on the filesystem in 'fspath'
        """
        if REQUEST and 'fspath' in REQUEST.form:
            self._setFSPath(REQUEST.form['fspath'])

        parent = self.aq_parent.aq_base
        if getattr(parent, 'isTopLevelPrincipiaApplicationObject', 0):
            self._dumpRoot(self.aq_parent)
        else:
            self._dumpFolder(self.aq_parent)

        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(
                  self.absolute_url()
                + '/editForm'
                + '?manage_tabs_message=Peers+dumped.'
                                        )
 
    #
    #   Utility methods
    #
    @security.private
    def _setFSPath(self, fspath):
        #   Canonicalize fspath.
        fspath = os.path.normpath(fspath)
        if not os.path.isabs(fspath):
            raise RunTimeError('Dumper Error: path must be absolute.')
        self.fspath = fspath


    @security.private
    def _buildPathString(self, path=None):
        #   Construct a path string, relative to self.fspath.
        if self.fspath is None:
            raise RunTimeError('Dumper Error: Path not set.')

        if path is None:
            path = self.fspath
        else:
            path = os.path.normpath(os.path.join(self.fspath, path))
        if os.path.isdir(path): # add a separator at the end for folders
            path = os.path.join(path, '')
        return path


    @security.private
    def _checkFSPath(self, path=None):
        #   Ensure that fspath/path exists.
        path = self._buildPathString(path)
        if not os.path.exists(path):
            os.makedirs(path)
        return path


    @security.private
    def _createFile(self, path, filename, mode='w'):
        #   Create/replace file;  return the file object.
        fullpath = "%s/%s" % (self._checkFSPath(path), filename)
        return open(fullpath, mode)


    @security.private
    def _createMetadataFile(self, path, filename, mode='w'):
        #   Create/replace file;  return the file object.
        extension = self.use_metadata_file and 'metadata' or 'properties'
        fullpath = "%s/%s.%s" % (self._checkFSPath(path),
                                 filename, extension)
        file = open(fullpath, mode)
        if self.use_metadata_file:
            file.write("[default]\n")
        else:
            file.write("[Default]\n")
        return file

    
    @security.private
    def _dumpObject(self, object, path=None):
        #   Dump one item, using path as prefix.
        try:
            print(object.meta_type)
            handler = self._handlers.get(object.meta_type, None)
            if handler is not None:
                handler(self, object, path)
                return 1
        except ConflictError:
            raise
        except:
            return -1
        return 0
            

    @security.private
    def _dumpObjects(self, objects, path=None):
        #   Dump each item, using path as prefix.
        dumped = []
        for object in objects:
            if self._dumpObject(object, path) > 0:
                id = object.getId()
                #if callable(id):
                #    id = id()
                dumped.append((id, object.meta_type))
        return dumped


    @security.private
    def _writeProperties(self, obj, file):
        propIDs = obj.propertyIds()
        propIDs.sort()  # help diff out :)
        for propID in propIDs:
            type = obj.getPropertyType(propID)
            value = obj.getProperty(propID)
            file.write('%s:%s=%s\n' % (propID, type, value))


    #
    #   Type-specific dumpers
    #
    @security.private
    def _dumpRoot(self, obj):
        self._dumpObjects(obj.objectValues())


    @security.private
    def _dumpFolder(self, obj, path=None):
        #   Recurse to dump items in a folder.
        if path is None:
            path = ''
        path = os.path.join(path, obj.id)
        file = self._createMetadataFile(path, '')
        self._writeProperties(obj, file)
        dumped = self._dumpObjects(obj.objectValues(), path)
        dumped.sort() # help diff out :)
        if self.use_metadata_file:
            file.write("\n[Objects]\n")
        else:
            file.close()
            file = self._createFile(path, '.objects')
        for id, meta in dumped:
            file.write('%s:%s\n' % (id, meta))
        file.close()


    @security.private
    def _dumpDTML( self, obj, path=None, suffix='dtml' ):
        #   Dump obj (assumed to be a DTML Method/Document) to the
        #   filesystem as a file, appending 'suffix' to the name.
        peer_id = obj.id()
        file = self._createFile( path, '%s.%s' % ( peer_id, suffix ) )
        text = obj.raw
        if text[-1] != '\n':
            text = '%s\n' % text
        file.write( text )
        file.close()

    @security.private
    def _dumpSecurityInfo(self, obj, file):
        if getattr(obj.aq_base, '_proxy_roles', None):
            file.write('proxy=%s\n' % ','.join(obj._proxy_roles))
            print('wrote proxy for %s' % obj.id)
        security_header_written = 0
        valid_roles = obj.valid_roles()
        for perm_dict in obj.permission_settings():
            perm_name = perm_dict['name']
            acquire = (perm_dict['acquire'] and 1) or 0
            roles = []
            for role_idx in range(len(valid_roles)):
                if perm_dict['roles'][role_idx]['checked']:
                    roles.append(valid_roles[role_idx])
            if roles or (acquire==0):
                if not security_header_written:
                    security_header_written = 1
                    file.write('\n[security]\n')
                file.write('%s=%d:%s\n' % (perm_name, acquire, ','.join(roles)))
                print('wrote permission for %s' % obj.id)

    @security.private
    def _dumpDTMLMethod( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a DTML Method) to the
        #   filesystem as a file, with the accompanying properties file.
        self._dumpDTML( obj, path )
        file = self._createMetadataFile( path, '%s.dtml' % obj.id() )
        if self.use_metadata_file:
            file.write( 'title=%s\n' % obj.title )
            self._dumpSecurityInfo(obj, file)
        else:
            file.write( 'title:string=%s\n' % obj.title )
        file.close()

    @security.private
    def _dumpZWikiPage( self, obj, path=None, suffix='zwiki' ):
        peer_id = obj.id()
        file = self._createFile( path, '%s.%s' % ( peer_id, suffix ) )
        text = obj.text()
        if text[-1] != '\n':
            text = '%s\n' % text
        file.write( text )
        file.close()

        if self.use_metadata_file:
            file = self._createMetadataFile( path, '%s.%s' % ( peer_id,suffix))
            self._writeProperties( obj, file )
            self._dumpSecurityInfo(obj, file)
            file.close()

    @security.private
    def _dumpDTMLDocument( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a DTML Document) to the
        #   filesystem as a file, with the accompanying properties file.
        self._dumpDTML( obj, path )
        file = self._createMetadataFile( path, '%s.dtml' % obj.id() )
        self._writeProperties( obj, file )
        file.close()

    @security.private
    def _dumpExternalMethod( self, obj, path=None ):
        #   Dump properties of obj (assumed to be an Externa Method) to the
        #   filesystem as a file.
        file = self._createMetadataFile( path, '%s.em' % obj.id )
        if self.use_metadata_file:
            file.write( 'title=%s\n' % obj.title )
            file.write( 'module=%s\n' % obj._module )
            file.write( 'function=%s\n' % obj._function )
            self._dumpSecurityInfo(obj, file)
        else:
            file.write( 'title:string=%s\n' % obj.title )
            file.write( 'module:string=%s\n' % obj._module )
            file.write( 'function:string=%s\n' % obj._function )
        file.close()


    @security.private
    def _dumpFileOrImage(self, obj, path=None):
        #   Dump properties of obj (assumed to be an Externa Method) to the
        #   filesystem as a file, with the accompanying properties file.
        print('dump file', obj.getId())
        file = self._createMetadataFile(path, '%s' % obj.getId())
        if self.use_metadata_file:
            file.write('title=%s\n' % obj.title)
            file.write('content_type=%s\n' % obj.content_type)
            file.write('precondition=%s\n' % obj.precondition)
        else:
            file.write('title:string=%s\n' % obj.title)
            file.write('content_type:string=%s\n' % obj.content_type)
            file.write('precondition:string=%s\n' % obj.precondition)
        file.close()
        file = self._createFile(path, obj.getId(), 'wb')
        data = obj.data
        file.write(data)
        # TODO: this is not working in Zope4
        #if type(data) == type(''):
        #    file.write(data)
        #else:
        #    while data is not None:
        #        file.write(data.data)
        #        data = data.next
        file.close()


    @security.private
    def _dumpPythonMethod( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a Python Method) to the
        #   filesystem as a file, with the accompanying properties file.
        body_lines = obj._body.split( '\n' )
        body = '\n    '.join( body_lines ) 
        text = "def %s(%s)\n\n    %s" % ( obj.id, obj._params, body )
        if text[-1] != '\n':
            text = '%s\n' % text
        file = self._createFile( path, '%s.py' % obj.id )
        file.write( text )
        file.close()
        file = self._createMetadataFile( path, '%s.py' % obj.id )
        if self.use_metadata_file:
            file.write( 'title=%s\n' % obj.title )
            self._dumpSecurityInfo(obj, file)
        else:
            file.write( 'title:string=%s\n' % obj.title )
        file.close()

    @security.private
    def _dumpPythonScript( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a Python Script) to the
        #   filesystem as a file, with the accompanying properties file.
        file = self._createFile( path, '%s.py' % obj.id )
        file.write( obj.read() )
        file.close()
        file = self._createMetadataFile( path, '%s.py' % obj.id )
        if self.use_metadata_file:
            file.write( 'title=%s\n' % obj.title )
            self._dumpSecurityInfo(obj, file)
        else:
            file.write( 'title:string=%s\n' % obj.title )
        file.close()

    @security.private
    def _dumpControllerPythonScript( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a Python Script) to the
        #   filesystem as a file, with the accompanying properties file.
        file = self._createFile( path, '%s.cpy' % obj.id )
        file.write( obj.read() )
        file.close()
        file = self._createMetadataFile( path, '%s.cpy' % obj.id )
        file.write( 'title:string=%s\n' % obj.title )
        file.close()

    @security.private
    def _dumpValidatorScript( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a Controller Validator) to the
        #   filesystem as a file, with the accompanying properties file.
        file = self._createFile( path, '%s.vpy' % obj.id )
        file.write( obj.read() )
        file.close()
        file = self._createMetadataFile( path, '%s.vpy' % obj.id )
        file.write( 'title:string=%s\n' % obj.title )
        file.close()

    @security.private
    def _dumpControllerPageTemplate( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a ZopeControllerPageTemplate) to the
        #   filesystem as a file, with the accompanying properties file.
        file = self._createFile( path, '%s.cpt' % obj.id )
        file.write( obj.read() )
        file.close()
        file = self._createMetadataFile( path, '%s.cpt' % obj.id )
        file.write( 'title:string=%s\n' % obj.title )
        file.close()

    @security.private
    def _dumpPageTemplate( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a ZopePageTemplate) to the
        #   filesystem as a file, with the accompanying properties file.
        file = self._createFile( path, '%s.pt' % obj.id )
        file.write( obj.read() )
        file.close()
        file = self._createMetadataFile( path, '%s.pt' % obj.id )
        self._writeProperties( obj, file )
        if self.use_metadata_file:
            self._dumpSecurityInfo(obj, file)
        file.close()

    @security.private
    def _dumpSQLMethod( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a SQL Method) to the
        #   filesystem as a file, with the accompanying properties file.
        file = self._createFile( path, '%s.zsql' % obj.id )
        text = "%s" % obj.src
        file.write(' <dtml-comment>\n')
        file.write( 'title:%s\n' % obj.title )
        file.write( 'arguments: %s\n'
                     % ' '.join(obj.arguments_src.splitlines() ) )
        file.write( 'connection_id:%s\n' % obj.connection_id )
        file.write( 'max_rows:%s\n' % obj.max_rows_ )
        file.write( 'max_cache:%s\n' % obj.max_cache_ )
        file.write( 'cache_time:%s\n' % obj.cache_time_ )
        file.write( 'class_name:%s\n' % obj.class_name_ )
        file.write( 'class_file:%s\n' % obj.class_file_ )
        file.write( '</dtml-comment>\n')
        if text[-1] != '\n':
            text = '%s\n' % text
        file.write( text )
        file.close()

    @security.private
    def _dumpZCatalog( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a ZCatalog) to the
        #   filesystem as a file, with the accompanying properties file.
        file = self._createFile( path, '%s.catalog' % obj.id )
        for brain in obj.searchResults():
            file.write( '%s\n' % obj.getpath( brain.data_record_id_ ) )
        file.close()
        file = self._createMetadataFile( path, '%s' % obj.id )
        file.write( 'title:string=%s\n' % obj.title )
        file.write( 'vocab_id:string=%s\n' % obj.vocab_id )
        file.write( 'threshold:int=%s\n' % obj.threshold )
        file.close()
        file = self._createFile( path, '%s.indexes' % obj.id )
        for index in obj.index_objects():
            file.write( '%s:%s\n' % ( index.id, index.meta_type ) )
        file.close()
        file = self._createFile( path, '%s.metadata' % obj.id )
        for column in obj.schema():
            file.write( '%s\n' % column )
        file.close()
    
    @security.private
    def _dumpZClass( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a ZClass) to the
        #   filesystem as a directory, including propertysheets and
        #   methods, as well as any nested ZClasses.
        if path is None:
            path = ''
        path = os.path.join( path, obj.id )
        file = self._createMetadataFile( path, '' )
        file.write( 'title:string=%s\n' % obj.title )
        file.write( 'metatype:string=%s\n' % obj._zclass_.meta_type )
        file.write( 'bases:tokens=%s\n'
                  % ','.join( map( lambda klass: str(klass), obj._zbases ) )
                  )
        file.write( 'class_id:int=%s\n' % obj._zclass_.__module__ )
        file.close()

        #   Dump icon
        file = self._createFile( path, '.icon', 'wb' )
        img = obj._zclass_.ziconImage
        data = img.data
        if type( data ) == type( '' ):
            file.write( data )
        else:
            while data is not None:
                file.write( data.data )
                data = data.next
        file.close()

        #   Dump views
        file = self._createFile( path, '.views' )
        for view in obj.propertysheets.views.data():
            file.write( '%s:%s\n' % ( view[ 'label' ], view[ 'action' ] ) )
        file.close()

        #   Dump property sheets.
        sheetpath = os.path.join( path, 'propertysheets' , 'common' )
        sheets = self._dumpObjects( obj.propertysheets.common.objectValues()
                                  , sheetpath )
        sheets.sort() # help diff out :)
        file = self._createFile( sheetpath, '.objects' )
        for id, meta in sheets:
            file.write( '%s:%s\n' % ( id, meta ) )
        file.close()

        #   Dump methods
        methodpath = os.path.join( path, 'propertysheets', 'methods' )
        methods = self._dumpObjects( obj.propertysheets.methods.objectValues()
                                   , methodpath )
        methods.sort() # help diff out :)
        file = self._createFile( methodpath, '.objects' )
        for id, meta in methods:
            file.write( '%s:%s\n' % ( id, meta ) )
        file.close()
    
    @security.private
    def _dumpZClassPropertySheet( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a ZClass) to the
        #   filesystem as a directory, including propertysheets and
        #   methods, as well as any nested ZClasses.
        file = self._createFile( path, obj.id )
        self._writeProperties( obj, file )
        file.close()

        file = self._createMetadataFile( path, obj.id )
        file.write( 'title:string=%s\n' % obj.title )
        file.close()
    
    @security.private
    def _dumpPermission( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a Zope Permission) to the
        #   filesystem as a .properties file.
        file = self._createMetadataFile( path, obj.id )
        file.write( 'title:string=%s\n' % obj.title )
        file.write( 'name:string=%s\n' % obj.name )
        file.close()

    @security.private
    def _dumpFactory( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a Zope Factory) to the
        #   filesystem as a .properties file.
        file = self._createMetadataFile( path, obj.id )
        file.write( 'title:string=%s\n' % obj.title )
        file.write( 'object_type:string=%s\n' % obj.object_type )
        file.write( 'initial:string=%s\n' % obj.initial )
        file.write( 'permission:string=%s\n' % obj.permission )
        file.close()

    @security.private
    def _dumpWizard( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a Wizard) to the
        #   filesystem as a directory, containing a .properties file
        #   and analogues for the pages.
        if path is None:
            path = ''
        path = os.path.join( path, obj.id )
        file = self._createMetadataFile( path, '' )
        file.write( 'title:string=%s\n' % obj.title )
        file.write( 'description:text=[[%s]]\n' % obj.description )
        file.write( 'wizard_action:string=%s\n' % obj.wizard_action )
        file.write( 'wizard_icon:string=%s\n' % obj.wizard_icon )
        file.write( 'wizard_hide_title:int=%s\n' % obj.wizard_hide_title )
        file.write( 'wizard_stepcount:int=%s\n' % obj.wizard_stepcount )
        file.close()

        pages = self._dumpObjects( obj.objectValues(), path )

        pages.sort() # help diff out :)
        file = self._createFile( path, '.objects' )
        for id, meta in pages:
            file.write( '%s:%s\n' % ( id, meta ) )
        file.close()

    @security.private
    def _dumpWizardPage( self, obj, path=None ):
        #   Dump properties of obj (assumed to be a WizardPage) to the
        #   filesystem as a file, appending ".wizardpage" to the name.
        self._dumpDTML( obj, path, 'wizardpage' )
        file = self._createMetadataFile( path, obj.id() )
        self._writeProperties( obj, file )
        file.close()

    @security.private
    def _dumpFormulatorForm( self, obj, path=None ):
        if path is None:
            path = ''
        file = self._createFile(path, obj.id + '.form')
        file.write(obj.get_xml())
        file.close()

    _handlers = { 'DTML Method'     : _dumpDTMLMethod
                , 'DTML Document'   : _dumpDTMLDocument
                , 'Folder'          : _dumpFolder
                , 'BTreeFolder2'    : _dumpFolder
                , 'External Method' : _dumpExternalMethod
                , 'File'            : _dumpFileOrImage
                , 'Image'           : _dumpFileOrImage
                , 'Python Method'   : _dumpPythonMethod
                , 'Script (Python)' : _dumpPythonScript
                , 'Controller Python Script' : _dumpControllerPythonScript
                , 'Controller Validator' : _dumpValidatorScript
                , 'Controller Page Template' : _dumpControllerPageTemplate
                , 'Page Template'   : _dumpPageTemplate
                , 'Z SQL Method'    : _dumpSQLMethod
                , 'ZCatalog'        : _dumpZCatalog
                , 'Z Class'         : _dumpZClass
                , 'Common Instance Property Sheet'
                                    : _dumpZClassPropertySheet
                , 'Zope Permission' : _dumpPermission
                , 'Zope Factory'    : _dumpFactory
                , 'Wizard'          : _dumpWizard
                , 'Wizard Page'     : _dumpWizardPage
                , 'Formulator Form' : _dumpFormulatorForm
               #, 'SQL DB Conn'     : _dumpDBConn
                , 'ZWiki Page'      : _dumpZWikiPage
                }

    @security.protected(USE_DUMPER_PERMISSION)
    def testDump( self, peer_path, path=None, REQUEST=None ):
        """
            Test dumping a single item.
        """
        obj = self.aq_parent.restrictedTraverse( peer_path )
        self._dumpObject( obj )
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect( self.absolute_url()
                                        + '/editForm'
                                        + '?manage_tabs_message=%s+dumped.'
                                        % peer_path
                                        )

# LOAD from file system

    @security.protected(USE_DUMPER_PERMISSION)
    def loadFromFS(self, REQUEST=None):
        """
           Browse recursively for files and metadata in the file system,
           starting in self.fspath, and create corresponding objects
           in Data.fs, in the same folder as the current Dumper object.
        """
        if REQUEST and 'fspath' in REQUEST.form:
            self._setFSPath(REQUEST.form['fspath'])

        parent = self.aq_parent.aq_base
        folder = self.aq_parent
        if getattr(parent, 'isTopLevelPrincipiaApplicationObject', 0):
            self._loadFolder(folder, '')
        else:
            self._loadFolder(folder, folder.getId())

        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(
                  self.absolute_url() + '/editForm' +
                  '?manage_tabs_message=Objects+loaded.')
 

    @security.private
    def _openMetadataFile(self, fullpath):
        #   open properties file in path;  return the file object.
        extension = self.use_metadata_file and '.metadata' or '.properties'
        metafile = open(fullpath + extension, mode='r')
        line = metafile.readline()
        # TODO: check contents of first line, per:
        #if self.use_metadata_file:
        #    file.write("[default]\n")
        #else:
        #    file.write("[Default]\n")
        return metafile
    

    @security.private
    def _readProperties(self, metafile):
        # Loading of properties is split in two parts: first read
        # into a dict then load as properties in _loadProperties
        # This separation allows some properties which are
        # actually attributes to be loaded differently
        props = {}
        for line in metafile:
            if line == '\n': break
            eq = line.find('=')
            prop = line[:eq]
            value = line[eq+1:-1]
            tmp = prop.split(':')
            propid = tmp[0]
            if len(tmp) == 2:
                otype = tmp[1]
            else:
                otype = 'string'
            if otype == 'ustring': otype = 'string'
            props[propid] = (value, otype)
        return props


    @security.private
    def _loadProperties(self, obj, props):
        # See note for _readProperties. If a property is loaded
        # separately as an attribute, then it should be removed
        # from the props dict before calling this function.
        if not props: return
        for propid, valtype in props.items():
            #try: not all objects are PropertyManager
            if obj.hasProperty(propid):
                obj._updateProperty(propid, valtype[0])
            else:
                obj._setProperty(propid, valtype[0], valtype[1])
            #except:
            #    print(propid, otype)
            #    print(sys.exc_info()[0])


    @security.private
    def _loadOneFile(self, folder, fname, meta, path=None):
        #   Load one file system item (file or folder)
        loader = self._loaders.get(meta, None)
        if loader is not None:
            loader(self, folder, fname, path)
        else: print('no loader')
            

    @security.private
    def _loadFiles(self, folder, files, path=None):
        #   Load each file (or folder) from the file system
        for fname, meta in files:
            print('load ', fname, meta)
            self._loadOneFile(folder, fname, meta, path)


    #
    #   Type-specific loaders
    #


    @security.private
    def _loadFolder(self, folder, fname='', path=None):
        #   Recursively load items from a folder.
        #   path is the relative file system path corresponding to folder,
        #   except for the top folder, which should be None and fname==''
        #   The folder contents are listed in .objects or .metadata[objects]
        #   Format: objectid:meta_type\n
        if path is None: 
            # top folder of fsdump, already exists
            # joins the path and adds a / at the end
            path = os.path.join(fname, '')
        else:
            # joins the path and adds a / at the end
            path = os.path.join(path, fname, '')
            obj = Folder(fname)
            folder._setObject(fname, obj)
            folder = folder._getOb(fname)
        fullpath = self._buildPathString(path)
        metafile = self._openMetadataFile(fullpath)
        props = self._readProperties(metafile)
        self._loadProperties(folder, props)
        if self.use_metadata_file:
            metafile.readline() # skip header "[Objects]"
        else:
            # close .metadata file and open .objects file
            metafile.close()
            metafile = open(fullpath + '/.objects', mode='r')
        files = []
        for line in metafile:
            print('Indexed file:', line[:-1])
            propid, meta = line[:-1].split(':')
            files.append((propid, meta))
        metafile.close()
        self._loadFiles(folder, files, path)


    @security.private
    def _loadPageTemplate(self, folder, fname, path=None):
        #   Load a ZopePageTemplate from the filesystem,
        #   with the accompanying properties file.
        fullpath = "%s/%s.pt" % (self._buildPathString(path), fname)
        objfile = open(fullpath, mode='r', encoding='latin-1')
        txt = objfile.read()
        objfile.close()
        obj = ZopePageTemplate(fname, txt)
        metafile = self._openMetadataFile(fullpath)
        props = self._readProperties(metafile)
        self._loadProperties(obj, props)
        metafile.close()
        folder._setObject(fname, obj)


    @security.private
    def _loadSQLMethod(self, folder, fname, path=None):
        #  Load attributes of a SQL Method from the filesystem
        #  ZSQL do not use properties, therefore the object's attributes
        #  are store together with the SQL statement in a <dtml-comment>
        fullpath = "%s/%s.zsql" % (self._buildPathString(path), fname)
        objfile = open(fullpath, mode='r')
        objfile.readline() # skip <dtml-comment>\n
        attrs = {}
        for i in range(8):
            line = objfile.readline()
            colon = line.find(':')
            propid = line[:colon]
            value = line[colon+1:-1]
            attrs[propid] = value
        objfile.readline() # skip </dtml-comment>\n
        text = objfile.read()
        obj = SQL(fname, attrs['title'], attrs['connection_id'],
                  attrs['arguments'], text)
        # TODO: advanced props
        #file.write( 'max_rows:%s\n' % obj.max_rows_ )
        #file.write( 'max_cache:%s\n' % obj.max_cache_ )
        #file.write( 'cache_time:%s\n' % obj.cache_time_ )
        #file.write( 'class_name:%s\n' % obj.class_name_ )
        #file.write( 'class_file:%s\n' % obj.class_file_ )
        objfile.close()
        folder._setObject(fname, obj)


    @security.private
    def _loadPythonScript(self, folder, fname, path=None):
        #   Load a python script from the file system
        #   and the accompanying properties file.
        fullpath = "%s/%s.py" % (self._buildPathString(path), fname)
        objfile = open(fullpath, mode='r', encoding='latin-1')
        text = objfile.read()
        objfile.close()
        obj = PythonScript(fname)
        obj.write(text)
        metafile = self._openMetadataFile(fullpath)
        line = metafile.readline()
        eq = line.find('=')
        prop = line[:eq]
        value = line[eq+1:-1]
        obj.ZPythonScript_setTitle(value)  
        metafile.close()
        folder._setObject(fname, obj)


    @security.private
    def _loadFile(self, folder, fname, path=None):
        fullpath = "%s/%s" % (self._buildPathString(path), fname)
        metafile = self._openMetadataFile(fullpath)
        props = self._readProperties(metafile)
        metafile.close()
        # code adapted from OFS/Image.py - manage_addFile
        # First, we create the file without data:
        obj = File(fname, props['title'][0], b'',
                   props['content_type'][0],
                   props['precondition'][0])
        folder._setObject(fname, obj)
        # Now we "upload" the data.  By doing this in two steps, we
        # can use a database trick to make the upload more efficient.
        objfile = open(fullpath, mode='rb')
        obj.manage_upload(objfile.read())
        objfile.close()
        #if content_type:
        #    obj.content_type = content_type
        # notify(ObjectCreatedEvent(newFile))


    @security.private
    def _loadImage(self, folder, fname, path=None):
        fullpath = "%s/%s" % (self._buildPathString(path), fname)
        metafile = self._openMetadataFile(fullpath)
        props = self._readProperties(metafile)
        metafile.close()
        # code adapted from OFS/Image.py - manage_addFile
        # First, we create the file without data:
        obj = Image(fname, props['title'][0], b'',
                   props['content_type'][0],
                   props['precondition'][0])
        folder._setObject(fname, obj)
        # Now we "upload" the data.  By doing this in two steps, we
        # can use a database trick to make the upload more efficient.
        objfile = open(fullpath, mode='rb')
        obj.manage_upload(objfile.read())
        objfile.close()
        #if content_type:
        #    obj.content_type = content_type
        # notify(ObjectCreatedEvent(newFile))


    @security.private
    def _loadExternalMethod( self, obj, path=None ):
        #   Dump properties of obj (assumed to be an Externa Method) to the
        #   filesystem as a file.
        file = self._createMetadataFile( path, '%s.em' % obj.id )
        if self.use_metadata_file:
            file.write( 'title=%s\n' % obj.title )
            file.write( 'module=%s\n' % obj._module )
            file.write( 'function=%s\n' % obj._function )
            self._dumpSecurityInfo(obj, file)
        else:
            file.write( 'title:string=%s\n' % obj.title )
            file.write( 'module:string=%s\n' % obj._module )
            file.write( 'function:string=%s\n' % obj._function )
        file.close()


    _loaders = { 'Folder'          : _loadFolder,
                 'Page Template'   : _loadPageTemplate,
                 'Z SQL Method'    : _loadSQLMethod,
                 'Script (Python)' : _loadPythonScript,
                 'File'            : _loadFile,
                 'Image'           : _loadImage
               }
"""
    _loaders = { 'DTML Method'     : _loadDTMLMethod
                , 'DTML Document'   : _loadDTMLDocument
                , 'Folder'          : _loadFolder
                , 'BTreeFolder2'    : _loadFolder
                , 'External Method' : _loadExternalMethod
                , 'Image'           : _loadFileOrImage
                , 'Python Method'   : _loadPythonMethod
                , 'Controller Python Script' : _loadControllerPythonScript
                , 'Controller Validator' : _loadValidatorScript
                , 'Controller Page Template' : _loadControllerPageTemplate
                , 'Page Template'   : _loadPageTemplate
                , 'ZCatalog'        : _loadZCatalog
                , 'Z Class'         : _loadZClass
                , 'Common Instance Property Sheet'
                                    : _loadZClassPropertySheet
                , 'Zope Permission' : _loadPermission
                , 'Zope Factory'    : _loadFactory
                , 'Wizard'          : _loadWizard
                , 'Wizard Page'     : _loadWizardPage
                , 'Formulator Form' : _loadFormulatorForm
               #, 'SQL DB Conn'     : _loadDBConn
                , 'ZWiki Page'      : _loadZWikiPage
                }
"""
