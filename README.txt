FSDump Product

 Author

  "Tres Seaver", mailto:tseaver@digicool.com, Digital Creations

 Overview

  FSDump grew out of an itch which many Zope developers have:
  through-the-web development is faster and easier to do, but
  causes significant deployment and configuration management
  problems.  Through-the-web code cannot (easily) be checked into
  CVS, or diffed to show changes, or grepped to find the source
  of an error message.

 Goals

  * The first goal is to ease the burden of getting TTW code
    under version control:  i.e., to make it possible to check
    a representation of the TTW code into CVS, and then to see
    what changes between versions.

  * Keep the file-system representations of the TTW objects 
    simple and "natural" (we are explicitly avoiding XML here).

  * Future goals might include:

    - Two-way migration (e.g., make changes to dumped items in
      vim/emacs, and then import those changes back into the
      TTW code).

 Installation

  * Unpack the product into the 'Products' directory of your
    Zope;  restart Zope.

 Usage

  * Use the "Add list" to create a "Dumper" instance in a folder
    (or Product) which contains the TTW code to be dumped.

  * Supply an absolute path to a directory on the filesystem
    in which the dumper is to create the files (note that the
    user as whom Zope is running needs write access to this
    directory).

  * Click the "Change and Dump" button to do the dump to the
    indicated directory.

 Mapping TTW Code to the Filesystem

  General Mapping

   * Create the most "natural" filesystem analogue for each TTW
     item:  Folders -> directories, DTML Methods/Documents ->
     DTML files, PythonMethods -> Python modules.

   * Trap non-inline properties in a companion file, with a
     '.properties' suffix.  Store one property per line, using
     'name:type=value' syntax.

   * Preserve enough metadata to be able to recreate the TTW
     object, preferably by *using its web interface.*  This rule
     is the chief differentiator (in concept) from pickling; we
     don't save state which cannot be set by a TTW manager.

  Specific Mappings
   
   'Folder'

    - Recursively store contained items into the folder's
      directory.

    - Store a list of the dumped items in an ".objects" file,
      one line per item, using the format, 'name:meta_type'.

   'Python Method'

    - Create a module containing a single top-level function
      definition, using the name, argument list, and body.

   'File' / 'Image'

    - Save the file contents themselves in binary format using
      the item's id.

   'SQL Method'
   
    - Inject the parameter list inline into the body, with a
      leading blank line.

   'ZCatalog'

    - Store the paths of the catalogued objects in a
      "<id>.catalog" file, one line per item.

    - Store the index definititions in a "<id>.indexes" file,
      one line per index, using the format, 'name:meta_type'.

    - Store the schema in a "<id>.metadata" file, one line per
      field name.

   'ZClass'

    - Map to a directory.

    - Store "basic" tab values in '.properties'

    - Store icon in '.icon'

    - Store propertysheets in 'propertysheets/common'.

    - Store method tab objects (includin nested ZClasses)
      in 'propertysheets/methods'.

   'Common Instance Property Sheet' (ZClass property sheet)

    - Store properties as name:type=value in file of same name.

   'Zope Permission'

    - Store values in "*.properties".

   'Zope Factory'

    - Store values in "*.properties".

   'Wizard'

    - Map to a directory.

    - Store properties in '.properties'.

    - Store pages.

   'WizardPage'

    - Store text in "*.wizardpage'.

    - Store properties in '*.properties'.
   
 Known Issues

  * Some types of metadata ('bobobase_modification_time') won't
    be exported as a property.

 ToDo's

  * Finish out the typelist for "standard" metatypes:

    - Database connectors

  * Integrate with the HelpSystem.

  * Add an ability to export permission mappings (for any
    permission which isn't acquired).

  * Add an ability to export local roles (??)

  * Introspect ZClass instances to export them using their
    propertysheets?

  * Make the dumper easier to extend (e.g., by adding
    *more* TTW code to emit FS code ;), or by registering
    handlers for new metatypes.)

