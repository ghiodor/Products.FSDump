Edit / Dump Dumper
==================

Description
-----------

The "Edit / Dump" view of an Dumper instance is used to set the
filesystem path to which the object's parent will be dumped, and
to initiate this dumping.
how the operations

Controls
--------

``ID``
    The id of the Dumper object (readonly)

``Filesystem path``
    The path under which the Dumper's parent will have its filesystem
    analog (a subdirectory) created.  All children of the Dumper's
    parent will have their analogs created under this subdirectory.
    E.g., if the value of this field is ``/tmp``, and the parent folder
    is called ``parent_folder``, then the dumper will create a
    subdirectory, ``/tmp/parent_folder``, and build objects in it
    corresponding to the dumper's "siblings".

``Use .metadata file``
    If checked, write a "new-style" .metadata file, in a format
    compatilbie with CMF 1.4 and later.  Properties go into the
    ``[Default]`` section.

``Change``
    Changes the filesystem mapping.

``Change and Dump``
    Changes the filesystem mapping and performs the dumping.
