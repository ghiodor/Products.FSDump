Mapping TTW Code to the Filesystem
==================================

General Mapping
---------------

- Create the most "natural" filesystem analogue for each TTW
  item:  Folders -> directories, DTML Methods/Documents ->
  DTML files, PythonMethods -> Python modules.

- Trap non-inline properties in a companion file, with a
  ``.properties`` suffix.  Store one property per line, using
  ``name:type=value`` syntax.

  * XXX: in companion ``.metadata`` file, store the properties
    in the ``[Default]`` section.

- Map the permission-role map in the ``[Permissions]`` section of the
  companion ``.metadata`` file (XXX this feature not present before
  the switch to ``.metadata``, although it might have mapped to the
  ``.security`` file supported by CMF 1.3)

- Map local roles in the ``[LocalRoles]`` section of the
  companion ``.metadata`` file (XXX this feature not present before
  the switch to ``.metadata``)

- Write proxy roles to a ``proxy`` property (XXX CMF 1.4 compatibility;
  this is an *ugly* spelling).  Should probably put it into a "prettier"
  spelling, as well, and lobby to change the spelling used in CMF.

- Preserve enough metadata to be able to recreate the TTW
  object, preferably by *using its web interface.*  This rule
  is the chief differentiator (in concept) from pickling; we
  don't save state which cannot be set by a TTW manager.

Specific Mappings
-----------------

Folder
%%%%%%

- Recursively store contained items into the folder's directory.

- Store a list of the dumped items in an ``.objects`` file,
  one line per item, using the format, ``name:meta_type``.

  * XXX: in ``.metadata`` file, store the same lines in an
    ``[Objects]`` directory.

File / Image
%%%%%%%%%%%%

- Save the file contents themselves in binary format using the item's id.

- Store properties in ``*.properties``.

DTMLMethod
%%%%%%%%%%

- Create a single file containng the text of the template.  Filename will
  have extension, ``.dtml``.

DTMLDocument
%%%%%%%%%%%%

- Create a single file containng the text of the template.  Filename will
  have extension, ``.dtml``.

- Store properties in ``*.properties``.

Python Script
%%%%%%%%%%%%%

- Create a module containing a single top-level function definition, using
  the "read" format (bindings in comments at the top).

PageTemplate
%%%%%%%%%%%%

- Create a single file containng the text of the template.  Filename will
  have extension, ``.pt``.

- Store properties in ``*.properties``.

SQL Method
%%%%%%%%%%

- Inject the parameter list inline into the body, with a leading blank line.

ZCatalog
%%%%%%%%

- Store the paths of the catalogued objects in a ``<id>.catalog`` file,
  one line per item.

- Store the index definititions in a ``<id>.indexes`` file,
  one line per index, using the format, ``name:meta_type``.

- Store the schema in a ``<id>.metadata`` file, one line per
  field name.

Controller Python Script
%%%%%%%%%%%%%%%%%%%%%%%%

- Create a module containing a single top-level function
  definition, using the "read" format (bindings in comments
  at the top).  Filename will have extension, ``.cpy``

- Store properties in ``*.properties``.

Controller Validator
%%%%%%%%%%%%%%%%%%%%

- Create a module containing a single top-level function
  definition, using the "read" format (bindings in comments
  at the top).  Filename will have extension, ``.vpy``

- Store properties in ``*.properties``.

Controller Page Template
%%%%%%%%%%%%%%%%%%%%%%%%

- Create a single file containng the text of the template.
  Filename will have extension, ``.cpt``.

- Store properties in ``*.properties``.


Mappings for Obsolete Types
---------------------------

Python Method
%%%%%%%%%%%%%

- Create a module containing a single top-level function
  definition, using the name, argument list, and body.

ZClass
%%%%%%

- Map to a directory.

- Store "basic" tab values in ``.properties``

- Store icon in ``.icon``

- Store propertysheets in ``propertysheets/common``.

- Store method tab objects (including nested ZClasses)
  in ``propertysheets/methods``.

Common Instance Property Sheet (ZClass property sheet)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

- Store properties as ``name:type=value`` in file of same name.

Zope Permission
%%%%%%%%%%%%%%%

- Store values in ``*.properties``.

Zope Factory
%%%%%%%%%%%%

- Store values in ``*.properties``.

Wizard
%%%%%%

- Map to a directory.

- Store properties in ``.properties``.

- Store pages.

WizardPage
%%%%%%%%%%

- Store text in ``*.wizardpage``.

- Store properties in ``*.properties``.
