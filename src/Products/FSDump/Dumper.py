""" Classes: Dumper

$Id$
"""

# TODO:
# separate errors into Dumper.errors
# - support encoding parameter to load text files
# - load security data
# - use manage_add; ask zope people to return object; 
# - document use of self in manage_add methods
# - report non-dumped objects due to error (continue dumping)
# - report which meta types do not have handlers
# - create a security decorator for Z2
# - dump should remove files not listed in .objects (option)
# - load should remove objects not listed in .objects (option)
# - verify that all types of properties are indeed loaded correctly
# -- at lease _updated tries to convert from string, not sure about _set, see:
# -- https://github.com/zopefoundation/Zope/blob/master/src/OFS/PropertyManager.py

# - on addDump, allow option to do only dump or only load 
#   this allows explicitly configured one-way syncs to avoid mistakes
# - add option to specify text file encodings
# - remove old format for properties (see createMetadataFile)
# - document .metadata format (check CMF one)
# - handlers should have a class!
# - handlers should have an interface supported by the objects themselves?

# CHANGES re fsdump 0.9.5:
# - supports zope 2 and 4, although loading into Zope 2 might not work if
#   encodings are changed.
# - it supports partial dumping/loading only of changed objects/files.
# - Indistinct handling between root ZODB folder and other folder: fsdump will 
# dump the objects of the folder that contains the FSDump object, regardless
# of which folder it is;
# - "_handlers" dictionary now returns a triple (extension, dumper, loader)
# - old format for dumping data is not supported (use only .metadata files)
# - functions would pass around the relative path and compute the full path
#   as needed (more than once). Now the absolute fis system path is passed
#   around.
# - currently loads ZPT using encoding='latin-1', change Z2ENC below for your needs


import os
import shutil
import sys
import time

PY3 = sys.version_info[0] == 3
if PY3:
    binary_type = bytes
else:
    binary_type = str

Z2ENC = 'latin-1' # replace this with the encoding used in your Zope 2 system
ZOPE = 4
try:
    from AccessControl.class_init import InitializeClass
except ImportError: # Zope2
    from Globals import InitializeClass
    ZOPE = 2
try:
    from AccessControl.SecurityInfo import ClassSecurityInfo
except ImportError:  # Zope2
    from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import change_proxy_roles
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from ZODB.POSException import ConflictError

# imports required for the loading of objects
from OFS.DTMLMethod import addDTMLMethod
from OFS.DTMLDocument import addDTMLDocument
from OFS.Folder import manage_addFolder
from OFS.Image import manage_addFile, manage_addImage
from Products.PageTemplates.ZopePageTemplate import manage_addPageTemplate
from Products.PythonScripts.PythonScript import manage_addPythonScript
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
from Products.ZSQLMethods.SQL import manage_addZSQLMethod

# ==== Using a Zope decorater to register a product
# It would be nice if a class could be declared with a Zope decorator
# that registers the class in the Zope environment.
# However, cannot do as follows because "context" (given by zope
# to "initialize") is not available in Dumper.py
# So, the decorator would have to be a zope framework function similar to 
# "initialize" and "initialize" would not have to be declared and called 
# in __init__.py
# def Zope(zclass, addform, addaction, permission, icon):
#     InitializeClass(zclass)
#     context.registerClass(zclass,
#                           constructors= (addform,
#                                          addaction),
#                           permission= permission,
#                           icon=icon
#   )
# mockup use of a Zope decorator to register a Meta type class
# permission= 'Add Dumper',
# icon='www/dumper.gif'
# @Zope(manage_addFSDumpForm, manage_addFSDump, permission, icon)

USE_DUMPER_PERMISSION = 'Use Dumper'

if ZOPE == 4:
    manage_addFSDumpForm = PageTemplateFile('www/addDumper', globals())
else:
    manage_addFSDumpForm = PageTemplateFile('www/addDumper-z2', globals())


def manage_addFSDump(self, id, fspath=None, use_metadata_file=0, REQUEST=None):
    """
       Add a Dumper object to the system
    """
    dumper = Dumper()
    dumper.id = id
    dumper.edit(fspath, use_metadata_file)
    self._setObject(id, dumper)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect('manage_main')


def initialize(context):
    """
       Function expected by zope in module's __init__.py to register a product
       (see Zope/OFS/Application.py)
       Keep initialization knowledge local in Dumper.py
    """
    InitializeClass(Dumper)
    context.registerClass(Dumper,
                          constructors = (manage_addFSDumpForm,
                                         manage_addFSDump),
                          permission = 'Add Dumper',
                          icon = 'www/dumper.gif')


class Dumper(SimpleItem):
    """
    """
    meta_type = 'Dumper'

    manage_options = ({ 'label'    : 'Edit'
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
    dump_all = 0
    load_all = 0
    tslastdump = None   # TimeStamp "%Y-%m-%d %H:%M:%S"
    tslastload = None   # TimeStamp "%Y-%m-%d %H:%M:%S"
    dumped = []         # files dumped at the last dump
    loaded = []         # files loaded at the last load
    dump_conflicts = [] # objects not dumped because older than file
    load_conflicts = [] # files not loaded because older than object

    #
    #   Management interface methods.
    #
    index_html = None

    security.declareProtected(USE_DUMPER_PERMISSION, 'editForm')
    if ZOPE == 4:
        editForm = PageTemplateFile('www/editDumper', globals())
    else:
        editForm = PageTemplateFile('www/editDumper-z2', globals())


    security.declareProtected(USE_DUMPER_PERMISSION, 'edit')
#    @security.protected(USE_DUMPER_PERMISSION)
    def edit(self, fspath, use_metadata_file, dump_all=0, load_all=0, REQUEST=None):
        """
            Update Dumper attributes.
        """
        #   Canonicalize fspath.
        self.fspath = os.path.normpath(fspath)
        self.use_metadata_file = use_metadata_file
        self.dump_all = dump_all # dump only objects newer than its file
        self.load_all = load_all # load only files newer than its object
        self._checkInput()

        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(
                  self.absolute_url()
                + '/editForm'
                + '?manage_tabs_message=Dumper+updated.')


    security.declareProtected(USE_DUMPER_PERMISSION, 'dumpToFS')
#    @security.protected(USE_DUMPER_PERMISSION)
    def dumpToFS(self, REQUEST=None):
        """
            Iterate recursively over our peers, creating simulacra
            of them on the filesystem in 'fspath'
        """
        if REQUEST and 'fspath' in REQUEST.form:
            fspath = REQUEST.form['fspath']
            use_metadata_file = REQUEST.form.get('use_metadata_file', 0)
            dump_all = REQUEST.form.get('dump_all', 0)
            load_all = REQUEST.form.get('load_all', 0)
            self.edit(fspath, use_metadata_file, dump_all, load_all)
        else:
            # make final validation tests in case of direct call
            self._checkInput()

        fspath = os.path.join(self.fspath, '')
        folder = self.aq_parent
        fspath = os.path.join(self.fspath, '') # adds separator
        self.dumped = []
        self.dump_conflicts = []
        self._dumpFolder(folder, fspath)
        self.tslastdump = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(
                  self.absolute_url()
                + '/editForm'
                + '?manage_tabs_message=Peers+dumped.'
                                       )

    #
    #   Methods for object tree browsing
    #

    security.declarePrivate('_dumpFolder')
#    @security.private
    def _dumpFolder(self, folder, fspath):
        """
           Recurse to dump items from a folder into a file system folder path.
           fspath must be an absolute path ending with a folder separator.
           It will also delete files/folders in the file system which no longer
           exist in the database. It does that by loading the current metadata
           file (if it exists) to compare with the list of dumped objects
        """
        objs = {}
        if os.path.exists(fspath):
            # load folder object list
            metafile = None
            if self.use_metadata_file:
                if os.path.exists(fspath + '.metadata'):
                    metafile = self._openMetadataFile(fspath)
                    # skip properties
                    props = self._readProperties(metafile)
                    # skip header "[Objects]"
                    try: # PY3
                        line = next(metafile)
                    except: #  py < 2.6
                        line = metafile.next()
                    # remember: readline() not compatible with line iterator
            elif os.path.exists(fspath + 'objects'):
                metafile = open(fspath + '.objects')
            # read list of file system objects into a dict objid -> meta
            # objects dumped will be removed from the dict and the remaining
            # objects will then be removed from the file system
            if metafile:
                for line in metafile:
                    objid, meta = line[:-1].split(':')
                    objs[objid] = meta
                metafile.close()
            if self.dump_all: self.dumped.append(fspath)
        else:
            os.makedirs(fspath)
            self.dumped.append(fspath)


        # dump objects of the folder; "dumped" includes all existing objects
        dumped = self._dumpObjects(folder, folder.objectValues(), fspath)
        dumped.sort() # help diff out :)

        # dump folder properties and object index
        metafile = self._createMetadataFile(fspath)
        self._writeProperties(folder, metafile)
        if self.use_metadata_file:
            metafile.write("\n[Objects]\n")
        else:
            metafile.close()
            metafile = open(fspath + '.objects', mode='w')
        for objid, meta, updated, objts in dumped:
            metafile.write('%s:%s\n' % (objid, meta))
            if updated and meta != 'Folder': #TODO: should use ext, not meta
                self.dumped.append((objts, meta, fspath + objid,))
            if objid in objs:
                del objs[objid] # object was not deleted
        metafile.close()

        # delete absent objects from the file system
        for objid, meta in objs.items():
            ext, dumper, loader = self._handlers.get(meta, ('', None, None))
            fspathobj = self._getFSPathObj(fspath, objid, ext)
            if ext == self._EXTDir:
                shutil.rmtree(fspathobj)
            else:
                os.remove(fspathobj)
                self._deleteMetadataFile(fspathobj)
            # TODO: keep list to show in UI


    security.declarePrivate('_dumpObjects')
#    @security.private
    def _dumpObjects(self, folder, objects, fspath):
        """
           Dump each item, using fspath as prefix.
           fspath must be an absolute path ending with a folder separator.
           Returns list of objects processed: [(objid, meta, dumped)]
        """
        dumped = [] # contains list of objects that can be dumped
        for obj in objects:
            objid = obj.getId()
            objts = self._getObjts(folder, obj)
            ext, dumper, loader = self._handlers.get(
                obj.meta_type, ('', None, None))
            if dumper is None: # unsupported meta_type
                continue
            fspathobj = self._getFSPathObj(fspath, objid, ext)

            # handle cases where dump is always done
            # if dump_all OR folder OR new object
            if self.dump_all \
               or ext == self._EXTDir \
               or not os.path.exists(fspathobj):
                if self._dumpObject(dumper, obj, fspathobj, ext) > 0:
                    dumped.append((objid, obj.meta_type, True, objts))
                continue

            # handle previous load/dump time-barriers
            if self.tslastdump and objts <= self.tslastdump:
                # skip untouched objects but keep for the index (.metadata)
                dumped.append((objid, obj.meta_type, False, objts))
                continue
            if self.tslastload and objts <= self.tslastload:
                # avoid dumping objects just loaded
                dumped.append((objid, obj.meta_type, False, objts))
                continue

            # dump only objects newer than corresponding file
            filets = self._getFilets(fspathobj)
            if objts <= filets:
                dumped.append((objid, obj.meta_type, False, objts))
                self.dump_conflicts.append((fspathobj, objts, filets))
                continue
            if self._dumpObject(dumper, obj, fspathobj, ext) > 0:
                dumped.append((objid, obj.meta_type, True, objts))
        return dumped


    security.declarePrivate('_dumpObject')
#    @security.private
    def _dumpObject(self, dumper, obj, fspath, ext):
        """   Dump one item, using fspath as prefix. """
        if ext == self._EXTMeta:
             # remove metadata extension (createMetadata does not expect it)
            fspath = os.splitext(fspath)[0]
        try:
            dumper(self, obj, fspath)
            return 1
        except ConflictError:
            raise
        except Exception as ex:
            self.dumped.append(('EXCEPTION dumping object:', fspath, str(ex)))
            return 0


    #
    #   Utility methods
    #


    security.declarePrivate('_getFSPathObj')
#    @security.private
    def _getFSPathObj(self, folderpath, objid, ext):
        """ Returns the absolute path for the object's main file.
            Since a dumped object can use more than one file,
            this method returns the "main" file that contains
            the contents of the object, if applicable, else returns the
            main metadata file.
            This is the file used to check timestamps when syncing changes.
        """
        if ext == self._EXTSame: # no extension applicable
            fname = objid
        elif ext == self._EXTDir:  # folders, separator at the end
            fname = os.path.join(objid, '')
        elif ext == self._EXTMeta:  # only a metadata file is used
            extension = self.use_metadata_file and '.metadata'\
                                                or '.properties'
            fname = objid + extension
        else:
            fname = objid + ext
        return folderpath + fname


    security.declarePrivate('_getObjts')
#    @security.private
    def _getObjts(self, folder, obj):
        """ Returns the time stamp for an object"""
        try:
            objts = folder.last_modified(obj) # %Y-%m-%d %H:%M
            # TODO: use binary representation from ob._p_mtime
            # But, is it compatible with file.getmtime()?
        except: # zope 2
            ts = obj.bobobase_modification_time()
            objts = ts.strftime("%Y-%m-%d %H:%M:%S")
        return objts


    security.declarePrivate('_getFilets')
#    @security.private
    def _getFilets(self, fspath):
        """ Returns the time stamp for a file"""
        ts = os.path.getmtime(fspath)
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


    security.declarePrivate('_checkInput')
#    @security.private
    def _checkInput(self):
        #  Validate Dumper parameters (fspath)
        if self.fspath is None:
            raise RuntimeError('Dumper Error: file system path not set.')
        if not os.path.isabs(self.fspath):
            raise RuntimeError('Dumper Error: file system path must be absolute.')
        if not os.path.exists(self.fspath):
            raise RuntimeError('Dumper Error: file system path must exist.')


    security.declarePrivate('_createMetadataFile')
#    @security.private
    def _createMetadataFile(self, fspath, mode='w'):
        # Create/replace file; 
        # return the metadata file object (*.properties or *.metadata)
        # TODO: it would be better to support only the .metadata format to
        #  simplify code and avoid syncing between dumps of different formats
        extension = self.use_metadata_file and 'metadata' or 'properties'
        fname = "%s.%s" % (fspath, extension)
        metafile = open(fname, mode)
        if self.use_metadata_file:
            metafile.write("[default]\n")
        else:
            metafile.write("[Default]\n")
        return metafile

    
    security.declarePrivate('_deleteMetadataFile')
#    @security.private
    def _deleteMetadataFile(self, fspath):
        """
           Delete the metadata file
        """
        extension = self.use_metadata_file and 'metadata' or 'properties'
        fname = "%s.%s" % (fspath, extension)
        os.remove(fname)

    
    security.declarePrivate('_writeProperties')
#    @security.private
    def _writeProperties(self, obj, metafile):
        if getattr(obj.aq_base, '_proxy_roles', None):
            metafile.write('proxy=%s\n' % ','.join(obj._proxy_roles))
        propIDs = obj.propertyIds()
        propIDs.sort()  # help diff out :)
        for propID in propIDs:
            proptype = obj.getPropertyType(propID)
            value = obj.getProperty(propID)
            if proptype == 'boolean' and isinstance(value, int):
                # it seems in old versions of zope/zodb/python boolean was a int
                # which causes inconsistent dumping as 1/0 instead of True/False
                # thus, force conversion to bool
                value = bool(value)
            metafile.write('%s:%s=%s\n' % (propID, proptype, value))


    security.declarePrivate('_dumpSecurityInfo')
#    @security.private
    def _dumpSecurityInfo(self, obj, metafile):
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
                    metafile.write('\n[security]\n')
                metafile.write('%s=%d:%s\n' % \
                    (perm_name, acquire, ','.join(roles)))


    #
    #   Type-specific dumpers
    #

    security.declarePrivate('_dumpDTML')
#    @security.private
    def _dumpDTML(self, obj, fspath):
        #   Dump obj (assumed to be a DTML Method/Document) to the
        #   filesystem as a file, appending 'suffix' to the name.
        objfile = open(fspath, mode='w')
        text = obj.raw
        if text[-1] != '\n':
            text = '%s\n' % text
        objfile.write(text)
        objfile.close()


    security.declarePrivate('_dumpDTMLMethod')
#    @security.private
    def _dumpDTMLMethod(self, obj, fspath):
        #   Dump properties of obj (assumed to be a DTML Method) to the
        #   filesystem as a file, with the accompanying properties file.
        self._dumpDTML(obj, fspath)
        metafile = self._createMetadataFile(fspath)
        if self.use_metadata_file:
            metafile.write('title=%s\n' % obj.title)
            self._dumpSecurityInfo(obj, metafile)
        else:
            metafile.write('title:string=%s\n' % obj.title)
        metafile.close()


    security.declarePrivate('_dumpDTMLDocument')
#    @security.private
    def _dumpDTMLDocument(self, obj, fspath):
        #   Dump properties of obj (assumed to be a DTML Document) to the
        #   filesystem as a file, with the accompanying properties file.
        self._dumpDTML(obj, fspath)
        metafile = self._createMetadataFile(fspath)
        self._writeProperties(obj, metafile)
        metafile.close()


    security.declarePrivate('_dumpExternalMethod')
#    @security.private
    def _dumpExternalMethod(self, obj, fspath):
        #   Dump properties of obj (assumed to be an External Method) to the
        #   filesystem as a file.
        objfile = open(fspath, mode='w')
        objfile.write('title:string=%s\n' % obj.title)
        objfile.write('module:string=%s\n' % obj._module)
        objfile.write('function:string=%s\n' % obj._function)
        objfile.close()
        if self.use_metadata_file:
            metafile = self._createMetadataFile(fspath)
            self._dumpSecurityInfo(obj, metafile)
            metafile.close()


    security.declarePrivate('_dumpFileOrImage')
#    @security.private
    def _dumpFileOrImage(self, obj, fspath):
        #   Dump properties of obj (assumed to be an Externa Method) to the
        #   filesystem as a file, with the accompanying properties file.
        metafile = self._createMetadataFile(fspath)
        if self.use_metadata_file:
            metafile.write('title=%s\n' % obj.title)
            metafile.write('content_type=%s\n' % obj.content_type)
            metafile.write('precondition=%s\n' % obj.precondition)
        else:
            metafile.write('title:string=%s\n' % obj.title)
            metafile.write('content_type:string=%s\n' % obj.content_type)
            metafile.write('precondition:string=%s\n' % obj.precondition)
        metafile.close()
        objfile = open(fspath, mode='wb')
        data = obj.data
        if type(data) == binary_type:
            objfile.write(data)
        else:
            while data is not None:
                objfile.write(data.data)
                data = data.next
        objfile.close()

    security.declarePrivate('_dumpPythonMethod')
#    @security.private
    def _dumpPythonMethod(self, obj, fspath):
        #   Dump properties of obj (assumed to be a Python Method) to the
        #   filesystem as a file, with the accompanying properties file.
        body_lines = obj._body.split('\n')
        body = '\n    '.join(body_lines) 
        text = "def %s(%s)\n\n    %s" % (obj.id, obj._params, body)
        if text[-1] != '\n':
            text = '%s\n' % text
        objfile = open(fspath, mode='w')
        objfile.write(text)
        objfile.close()
        metafile = self._createMetadataFile(fspath)
        if self.use_metadata_file:
            metafile.write('title=%s\n' % obj.title)
            self._dumpSecurityInfo(obj, metafile)
        else:
            metafile.write('title:string=%s\n' % obj.title)
        metafile.close()


    security.declarePrivate('_dumpPythonScript')
#    @security.private
    def _dumpPythonScript(self, obj, fspath):
        #   Dump properties of obj (assumed to be a Python Script) to the
        #   filesystem as a file, with the accompanying properties file.
        objfile = open(fspath, mode='w')
        objfile.write(obj.read())
        objfile.close()
        metafile = self._createMetadataFile(fspath)
        if self.use_metadata_file:
            metafile.write('title=%s\n' % obj.title)
            self._dumpSecurityInfo(obj, metafile)
        else:
            metafile.write('title:string=%s\n' % obj.title)
        metafile.close()


    security.declarePrivate('_dumpControllerPythonScript')
#    @security.private
    def _dumpControllerPythonScript(self, obj, fspath):
        #   Dump properties of obj (assumed to be a Python Script) to the
        #   filesystem as a file, with the accompanying properties file.
        objfile = open(fspath, mode='w')
        objfile.write(obj.read())
        objfile.close()
        metafile = self._createMetadataFile(fspath)
        metafile.write('title:string=%s\n' % obj.title)
        metafile.close()


    security.declarePrivate('_dumpValidatorScript')
#    @security.private
    def _dumpValidatorScript(self, obj, fspath):
        #   Dump properties of obj (assumed to be a Controller Validator) to
        #   the filesystem as a file, with the accompanying properties file.
        objfile = open(fspath, mode='w')
        objfile.write(obj.read())
        objfile.close()
        metafile = self._createMetadataFile(fspath)
        metafile.write('title:string=%s\n' % obj.title)
        metafile.close()


    security.declarePrivate('_dumpControllerPageTemplate')
#    @security.private
    def _dumpControllerPageTemplate(self, obj, fspath):
        #   Dump properties of obj (assumed to be a ZopeControllerPageTemplate)
        #   to the filesystem as a file, with the accompanying properties file.
        objfile = open(fspath, mode='w')
        objfile.write(obj.read())
        objfile.close()
        metafile = self._createMetadataFile(fspath)
        metafile.write('title:string=%s\n' % obj.title)
        metafile.close()


    security.declarePrivate('_dumpPageTemplate')
#    @security.private
    def _dumpPageTemplate(self, obj, fspath):
        #   Dump contents of obj (assumed to be a ZopePageTemplate) to the
        #   filesystem as a file, with the accompanying properties file.
        objfile = open(fspath, mode='w')
        objfile.write(obj.read())
        objfile.close()
        metafile = self._createMetadataFile(fspath)
        self._writeProperties(obj, metafile)
        if self.use_metadata_file:
            self._dumpSecurityInfo(obj, metafile)
        metafile.close()


    security.declarePrivate('_dumpSQLMethod')
#    @security.private
    def _dumpSQLMethod(self, obj, fspath):
        #   Dump properties of obj (assumed to be a SQL Method) to the
        #   filesystem as a file, with the accompanying properties file.
        objfile = open(fspath, mode='w')
        text = "%s" % obj.src
        objfile.write(' <dtml-comment>\n')
        objfile.write('title:%s\n' % obj.title)
        objfile.write('arguments:%s\n'
                     % ' '.join(obj.arguments_src.splitlines()))
        objfile.write('connection_id:%s\n' % obj.connection_id)
        objfile.write('max_rows:%s\n' % obj.max_rows_)
        objfile.write('max_cache:%s\n' % obj.max_cache_)
        objfile.write('cache_time:%s\n' % obj.cache_time_)
        objfile.write('class_name:%s\n' % obj.class_name_)
        objfile.write('class_file:%s\n' % obj.class_file_)
        objfile.write('</dtml-comment>\n')
        if text[-1] != '\n':
            text = '%s\n' % text
        objfile.write(text)
        objfile.close()


    security.declarePrivate('_dumpZCatalog')
#    @security.private
    def _dumpZCatalog(self, obj, fspath):
        #   Dump properties of obj (assumed to be a ZCatalog) to the
        #   filesystem as a file, with the accompanying properties file.
        objfile = open(fspath, mode='w')
        for brain in obj.searchResults():
            objfile.write('%s\n' % obj.getpath(brain.data_record_id_))
        objfile.close()
        metafile = self._createMetadataFile(fspath)
        metafile.write('title:string=%s\n' % obj.title)
        metafile.write('vocab_id:string=%s\n' % obj.vocab_id)
        metafile.write('threshold:int=%s\n' % obj.threshold)
        metafile.close()
        fspath.replace()
        objfile = open(fspath.replace('.catalog', '.indexes'), mode='w')
        for index in obj.index_objects():
            objfile.write('%s:%s\n' % (index.id, index.meta_type))
        objfile.close()
        objfile = open(fspath.replace('.catalog', '.metadata'), mode='w')
        for column in obj.schema():
            objfile.write('%s\n' % column)
        objfile.close()


    security.declarePrivate('_dumpZClass')
#    @security.private
    def _dumpZClass(self, obj, fspath):
        #   Dump properties of obj (assumed to be a ZClass) to the
        #   filesystem as a directory, including propertysheets and
        #   methods, as well as any nested ZClasses.
        metafile = self._createMetadataFile(fspath)
        metafile.write('title:string=%s\n' % obj.title)
        metafile.write('metatype:string=%s\n' % obj._zclass_.meta_type)
        metafile.write('bases:tokens=%s\n'
                  % ','.join(map(lambda klass: str(klass), obj._zbases))
                 )
        metafile.write('class_id:int=%s\n' % obj._zclass_.__module__)
        metafile.close()

        #   Dump icon
        objfile = open(fspath + '.icon', mode='wb')
        img = obj._zclass_.ziconImage
        data = img.data
        if type(data) == binary_type:
            objfile.write(data)
        else:
            while data is not None:
                objfile.write(data.data)
                data = data.next
        objfile.close()

        #   Dump views
        objfile = open(fspath + '.views', mode='w')
        for view in obj.propertysheets.views.data():
            objfile.write('%s:%s\n' % (view[ 'label' ], view[ 'action' ]))
        objfile.close()

        #   Dump property sheets.
        sheetpath = os.path.join(fspath, 'propertysheets', 'common', '')
        if not os.path.exists(sheetpath):
            os.makedirs(sheetpath)
        sheets = self._dumpObjects(obj.propertysheets.common,
            obj.propertysheets.common.objectValues(), sheetpath)
        sheets.sort() # help diff out :)
        metafile = open(sheetpath + '.objects', mode='w')
        for objid, meta in sheets:
            metafile.write('%s:%s\n' % (objid, meta))
        metafile.close()

        #   Dump methods
        methodpath = os.path.join(fspath, 'propertysheets', 'methods', '')
        if not os.path.exists(methodpath):
            os.makedirs(methodpath)
        sheets = self._dumpObjects(obj.propertysheets.methods,
            obj.propertysheets.methods.objectValues(), methodpath)
        methods.sort() # help diff out :)
        metafile = open(methodpath + '.objects', mode='w')
        for objid, meta in methods:
            metafile.write('%s:%s\n' % (objid, meta))
        metafile.close()

    
    security.declarePrivate('_dumpZClassPropertySheet')
#    @security.private
    def _dumpZClassPropertySheet(self, obj, fspath):
        #   Dump properties of obj (assumed to be a ZClassPropertySheet) to the
        #   filesystem as a directory.
        propfile = open(fspath, mode='w')
        self._writeProperties(obj, propfile)
        propfile.close()

        metafile = self._createMetadataFile(fspath)
        metafile.write('title:string=%s\n' % obj.title)
        metafile.close()

    
    security.declarePrivate('_dumpPermission')
#    @security.private
    def _dumpPermission(self, obj, fspath):
        #   Dump properties of obj (assumed to be a Zope Permission) to the
        #   filesystem as a .properties file.
        metafile = self._createMetadataFile(fspath)
        metafile.write('title:string=%s\n' % obj.title)
        metafile.write('name:string=%s\n' % obj.name)
        metafile.close()


    security.declarePrivate('_dumpFactory')
#    @security.private
    def _dumpFactory(self, obj, fspath):
        #   Dump properties of obj (assumed to be a Zope Factory) to the
        #   filesystem as a .properties file.
        metafile = self._createMetadataFile(fspath)
        metafile.write('title:string=%s\n' % obj.title)
        metafile.write('object_type:string=%s\n' % obj.object_type)
        metafile.write('initial:string=%s\n' % obj.initial)
        metafile.write('permission:string=%s\n' % obj.permission)
        metafile.close()


    security.declarePrivate('_dumpWizard')
#    @security.private
    def _dumpWizard(self, obj, fspath):
        #   Dump properties of obj (assumed to be a Wizard) to the
        #   filesystem as a directory, containing a .properties file
        #   and analogues for the pages.
        metafile = self._createMetadataFile(fspath)
        metafile.write('title:string=%s\n' % obj.title)
        metafile.write('description:text=[[%s]]\n' % obj.description)
        metafile.write('wizard_action:string=%s\n' % obj.wizard_action)
        metafile.write('wizard_icon:string=%s\n' % obj.wizard_icon)
        metafile.write('wizard_hide_title:int=%s\n' % obj.wizard_hide_title)
        metafile.write('wizard_stepcount:int=%s\n' % obj.wizard_stepcount)
        metafile.close()

        pages = self._dumpObjects(obj, obj.objectValues(), fspath)

        pages.sort() # help diff out :)
        objfile = open(fspath + '.objects', mode='w')
        for objid, meta in pages:
            objfile.write('%s:%s\n' % (objid, meta))
        objfile.close()


    security.declarePrivate('_dumpWizardPage')
#    @security.private
    def _dumpWizardPage(self, obj, fspath):
        #   Dump properties of obj (assumed to be a WizardPage) to the
        #   filesystem as a file, appending ".wizardpage" to the name.
        self._dumpDTML(obj, fspath)
        metafile = self._createMetadataFile(fspath)
        self._writeProperties(obj, metafile)
        metafile.close()


    security.declarePrivate('_dumpFormulatorForm')
#    @security.private
    def _dumpFormulatorForm(self, obj, fspath):
        objfile = open(fspath, mode='w')
        objfile.write(obj.get_xml())
        objfile.close()


    security.declarePrivate('_dumpZWikiPage')
#    @security.private
    def _dumpZWikiPage(self, obj, fspath):
        peer_id = obj.id()
        objfile = open(fspath, mode='w')
        text = obj.text()
        if text[-1] != '\n':
            text = '%s\n' % text
        objfile.write(text)
        objfile.close()

        if self.use_metadata_file:
            metafile = self._createMetadataFile(fspath)
            self._writeProperties(obj, metafile)
            self._dumpSecurityInfo(obj, metafile)
            metafile.close()


    security.declareProtected(USE_DUMPER_PERMISSION, 'testDump')
#    @security.protected(USE_DUMPER_PERMISSION)
    def testDump(self, peer_path, path=None, REQUEST=None):
        """
            Test dumping a single item.
        """
        obj = self.aq_parent.restrictedTraverse(peer_path)
        self._dumpObject(obj)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self.absolute_url()
                                        + '/editForm'
                                        + '?manage_tabs_message=%s+dumped.'
                                        % peer_path
                                       )

    ########
    ##  LOAD from file system
    ########

    security.declareProtected(USE_DUMPER_PERMISSION, 'loadFromFS')
    #    @security.protected(USE_DUMPER_PERMISSION)
    def loadFromFS(self, REQUEST=None):
        """
           Browse recursively for files and metadata in the file system,
           starting in self.fspath, and create corresponding objects
           in Data.fs, in the same folder as the current Dumper object.
        """
        if REQUEST and 'fspath' in REQUEST.form:
            fspath = REQUEST.form['fspath']
            use_metadata_file = REQUEST.form.get('use_metadata_file', 0)
            dump_all = REQUEST.form.get('dump_all', 0)
            load_all = REQUEST.form.get('load_all', 0)
            self.edit(fspath, use_metadata_file, dump_all, load_all)

        fspath = os.path.join(self.fspath, '')
        folder = self.aq_parent # fsdump instance container
        self.loaded = []
        self.load_conflicts = []
        self._loadFolder(folder, '', fspath)
        self.tslastload = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self.absolute_url()
                                      + '/editForm'
                                      + '?manage_tabs_message=Objects+loaded.')
 

    security.declarePrivate('_loadFolder')
    #    @security.private
    def _loadFolder(self, container, foldername, fspath):
        """
           Load fs folder foldername into ZODB container (recursive)
           The folder contents are listed in .objects or .metadata[objects]
           Format: objectid:meta_type\n
           It will also delete files/folders in the ZODB database if they
           no longer exist in the file system.
           It does that by loading a possibly existing metadata file to compare
           with the list of dumped objects
           Note: files created outside zope, e.g., by vim, need to be
                 registered in .metadata (or .objects)
        """
        if foldername == '':
            # top folder of fsdump, it already exists, it's "container"
            folder = container
        else:
            # create folder in DB if it doesn't exist
            if ZOPE == 4:
                folder = container.get(foldername, None)
            else:
                if container.hasObject(foldername):
                    folder = container._getOb(foldername, None)
                else:
                    folder = None
            if folder is None:
                manage_addFolder(container, foldername)
                if ZOPE == 4:
                    folder = container.get(foldername)
                else:
                    folder = container._getOb(foldername, None)
        metafile = self._openMetadataFile(fspath)
        props = self._readProperties(metafile)
        self._loadProperties(folder, props)
        if self.use_metadata_file:
            try: # PY3
                line = next(metafile) # skip header "[Objects]"
            except: #  py < 2.6
                line = metafile.next() # skip header "[Objects]"
            # remember readline() not compatible with line iterator
        else:
            # close .metadata file and open .objects file
            metafile.close()
            metafile = open(fspath + '.objects')
        # load object list from file system, possibly partial, i.e.,
        # without new fs objects that might have been created with an editor
        # and not registered in .metadata
        objs = {}
        for line in metafile:
            objid, meta = line[:-1].split(':')
            objs[objid] = meta
        metafile.close()
        self._loadObjects(folder, objs, fspath)
        # delete ZODB objects no longer in the file system
        # unless they are not supported, keep them
        for obj in folder.objectValues(): 
            meta = obj.meta_type
            ext, dumper, loader = self._handlers.get(meta, ('', None, None))
            if not dumper: continue # don't touch unsupported objects
            objid = obj.getId()
            if objid in objs: continue # skip objects which exist in FS
            folder.manage_delObjects([objid])
            # TODO: keep list to show in UI


    security.declarePrivate('_loadObjects')
#    @security.private
    def _loadObjects(self, folder, objs, fspath):
        #   Load each obj (or folder) listed in objs from the file system
        # objs is a dict objid -> meta
        for objid, meta in objs.items():
            ext, dumper, loader = self._handlers.get(
                meta, ('', None, None))
            if loader is None: # unsupported meta_type
                continue
            fspathobj = self._getFSPathObj(fspath, objid, ext)

            # handle cases where load is always done
            obj = None
            if ZOPE == 4:
                obj = folder.get(objid, None)
            else:
                obj = folder._getOb(objid, None)
            # if load_all objects OR new object OR is folder
            if self.load_all \
               or obj is None \
               or ext == self._EXTDir:
                self._loadObject(loader, folder, objid, fspathobj, ext)
                continue

            # hanlde load/dump time barriers
            filets = self._getFilets(fspathobj)
            if self.tslastload and filets <= self.tslastload:
                # skip files older than last load
                continue
            if self.tslastdump and filets <= self.tslastdump:
                # skip files just dumped
                continue

            # load only files newer than corresponding (existing) objects
            objts = self._getObjts(folder, obj)
            if  filets <= objts:
                self.load_conflicts.append(fspathobj)
                continue
            self._loadObject(loader, folder, objid, fspathobj, ext)


    security.declarePrivate('_loadObject')
#    @security.private
    def _loadObject(self, loader, folder, objid, fspath, ext):
        """   Load file fspath as an object with name objid into folder. """
        if ext == self._EXTMeta:
            fspath = os.splitext(fspath)[0]
        if ext != self._EXTDir and folder.hasObject(objid):
            folder._delObject(objid)
        try:
            loader(self, folder, objid, fspath)
            self.loaded.append(fspath)
            return 1
        except:
            return 0


    ## Utility methods


    security.declarePrivate('_openMetadataFile')
#    @security.private
    def _openMetadataFile(self, fspath, mode='r'):
        #   open properties file in path;  return the file object.
        extension = self.use_metadata_file and '.metadata' or '.properties'
        metafile = open(fspath + extension, mode=mode)
        # get rid of the section header ([Default])
        try:  # PY3
            line = next(metafile)
        except StopIteration:
            # The metadata file is empty
            # It should not happen unless the dump broke previously and
            # the file was not created correctly
            # It will be recreated at some point
            pass
        except: # py < 2.6
            line = metafile.next()
        # TODO: check contents of first line, per:
        #if self.use_metadata_file:
        #    file.write("[default]\n")
        #else:
        #    file.write("[Default]\n")
        return metafile
    

    security.declarePrivate('_readProperties')
#    @security.private
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


    security.declarePrivate('_loadProperties')
#    @security.private
    def _loadProperties(self, obj, props):
        # See note for _readProperties. If a property is loaded
        # separately as an attribute, then it should be removed
        # from the props dict before calling this function.
        if not props: return
        if 'proxy' in props:
            proxy = props.pop('proxy')
            #obj.manage_proxy(proxy.split(','))
            obj._proxy_roles = tuple(proxy.split(','))
        for propid, valtype in props.items():
            #try: not all objects are PropertyManager
            if obj.hasProperty(propid):
                obj._updateProperty(propid, valtype[0])
            else:
                obj._setProperty(propid, valtype[0], valtype[1])
            #except:
            #    print(propid, otype)
            #    print(sys.exc_info()[0])


    security.declarePrivate('_loadSecurityInfo')
#    @security.private
    def _loadSecurityInfo(self, obj, metafile):
        # not yet implemented, need to figure out api to register permissions. 
        # in AccessControl/rolemanager.py manage_permission
        # manage_permission(self, permission_to_manage, roles=[], acquire=0)
        # note that proxy roles are loaded in _loadProperties
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


    #
    #   Type-specific loaders
    #


    security.declarePrivate('_loadPageTemplate')
#    @security.private
    def _loadPageTemplate(self, folder, objid, fspath):
        #   Load a ZopePageTemplate from the filesystem,
        #   with the accompanying properties file.
        if PY3:
            objfile = open(fspath, mode='r', encoding=Z2ENC)
        else: # py2
            objfile = open(fspath, mode='r')
        txt = objfile.read()
        objfile.close()
        manage_addPageTemplate(folder, objid, text=txt)
        if ZOPE == 4:
            obj = folder[objid]
        else:
            obj = folder._getOb(objid, None)
        metafile = self._openMetadataFile(fspath)
        props = self._readProperties(metafile)
        self._loadProperties(obj, props)
        metafile.close()


    security.declarePrivate('_loadSQLMethod')
#    @security.private
    def _loadSQLMethod(self, folder, objid, fspath):
        #  Load attributes of a SQL Method from the filesystem
        #  ZSQL do not use properties, therefore the object's attributes
        #  are store together with the SQL statement in a <dtml-comment>
        objfile = open(fspath, mode='r')
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
        objfile.close()
        manage_addZSQLMethod(folder, objid, attrs['title'],
            attrs['connection_id'], attrs['arguments'], text)
        if ZOPE == 4:
            obj = folder[objid]
        else:
            obj = folder._getOb(objid, None)
        obj.manage_advanced(attrs['max_rows'], attrs['max_cache'],
            attrs['cache_time'], attrs['class_name'], attrs['class_file'])


    security.declarePrivate('_loadPythonScript')
#    @security.private
    def _loadPythonScript(self, folder, objid, fspath):
        #   Load a python script from the file system
        #   and the accompanying properties file.
        # read title from metadata
        metafile = self._openMetadataFile(fspath)
        try:  # PY3
            line = next(metafile)
        except: # py < 2.6
            line = metafile.next()
        eq = line.find('=')
        prop = line[:eq]
        title = line[eq+1:-1]
        manage_addPythonScript(folder, objid, title)
        if ZOPE == 4:
            obj = folder[objid]
        else:
            obj = folder._getOb(objid, None)
        try: # PY3
            objfile = open(fspath, mode='r', encoding=Z2ENC)
        except: # py2
            objfile = open(fspath, mode='r')
        text = objfile.read()
        objfile.close()
        obj.write(text)
        # TODO: load permissions
        metafile.close()


    security.declarePrivate('_loadFile')
#    @security.private
    def _loadFile(self, folder, objid, fspath):
        """ Load a file """
        metafile = self._openMetadataFile(fspath)
        props = self._readProperties(metafile)
        metafile.close()
        objfile = open(fspath, mode='rb')
        title = props['title'][0]
        ct = props['content_type'][0]
        pc = props['precondition'][0]
        manage_addFile(folder, objid, objfile, title, pc, ct)
        objfile.close()


    security.declarePrivate('_loadImage')
#    @security.private
    def _loadImage(self, folder, objid, fspath):
        """ Load an image """
        metafile = self._openMetadataFile(fspath)
        props = self._readProperties(metafile)
        metafile.close()
        objfile = open(fspath, mode='rb')
        title = props['title'][0]
        ct = props['content_type'][0]
        pc = props['precondition'][0]
        manage_addImage(folder, objid, objfile, title, pc, ct)
        objfile.close()


    security.declarePrivate('_loadExternalMethod')
#    @security.private
    def _loadExternalMethod(self, folder, objid, fspath):
        objfile = open(fspath, mode='r')
        props = self._readProperties(objfile)
        manage_addExternalMethod(
            folder,
            objid,
            props['title'][0],
            props['module'][0],
            props['function'][0])
        # TODO:  load security self._dumpSecurityInfo(obj, file)
        # metafile = self._openMetadataFile(fspath)
        # props = self._readProperties(metafile)
        metafile.close()


    security.declarePrivate('_loadDTMLMethod')
#    @security.private
    def _loadDTMLMethod(self, folder, objid, fspath):
        #   Load objid from file fspath with the accompanying properties file.
#        obj = self._loadDTML(folder, objid, fspath)
        objfile = open(fspath, mode='r')
        addDTMLMethod(folder, objid, '', objfile)
        obj = folder[objid]
        metafile = self._openMetadataFile(fspath)
        props = self._readProperties(metafile)
        obj.title = props['title'][0]
#        self._dumpSecurityInfo(obj, metafile)
        metafile.close()


    security.declarePrivate('_loadDTMLDocument')
#    @security.private
    def _loadDTMLDocument(self, folder, objid, fspath):
        #   Load objid from file fspath with the accompanying properties file.
        objfile = open(fspath, mode='r')
        addDTMLDocument(folder, objid, '', objfile)
        obj = folder[objid]
        metafile = self._openMetadataFile(fspath)
        props = self._readProperties(metafile)
        self._loadProperties(obj, props)
#        self._dumpSecurityInfo(obj, metafile)
        metafile.close()


    # codes used for extension in _HDLext field of _handler tuples:
    # '=' : dump a file object without extra extension
    # '-' : dump only metadata file
    # '/'  : container object (os.join will append '' as /
    # otherwise, dump the object with the extension indicated
    _EXTSame, _EXTMeta, _EXTDir = ('=', '-', '/')
    # named indexes for tuple of handler
    _HDLext, _HDLdumper, _HDLloader = range(3)
    _handlers = {
        'DTML Method'     : ('.dtml', _dumpDTMLMethod, _loadDTMLMethod),
        'DTML Document'   : ('.dtml', _dumpDTMLDocument, _loadDTMLDocument),
        'Folder'          : ('/', _dumpFolder, _loadFolder),
        'BTreeFolder2'    : ('/', _dumpFolder, _loadFolder),
        'External Method' : ('.em', _dumpExternalMethod, _loadExternalMethod),
        'Zope Factory'    : ('-', _dumpFactory, None),
        'File'            : ('=', _dumpFileOrImage, _loadFile),
        'Image'           : ('=', _dumpFileOrImage, _loadImage),
        'Formulator Form' : ('.form', _dumpFormulatorForm, None),
        'Python Method'   : ('.py', _dumpPythonMethod, None),
        'Script (Python)' : ('.py', _dumpPythonScript, _loadPythonScript),
        'Controller Python Script' :
                            ('.cpy', _dumpControllerPythonScript, None),
        'Controller Validator' : ('.vpy', _dumpValidatorScript, None),
        'Controller Page Template' :
                            ('.cpt', _dumpControllerPageTemplate, None),
        'Page Template'   : ('.pt', _dumpPageTemplate, _loadPageTemplate),
        'Zope Permission' : ('-', _dumpPermission, None),
        'Z SQL Method'    : ('.zsql', _dumpSQLMethod, _loadSQLMethod),
        'ZCatalog'        : ('.catalog', _dumpZCatalog, None),
        'Z Class'         : ('/', _dumpZClass, None),
        'Common Instance Property Sheet'
                          : ('/', _dumpZClassPropertySheet, None),
        'Wizard'          : ('/', _dumpWizard, None),
        'Wizard Page'     : ('.wizardpage', _dumpWizardPage, None),
        # 'SQL DB Conn'     : ('.db', _dumpDBConn, None),
        'ZWiki Page'      : ('.zwiki', _dumpZWikiPage, None)
        }


