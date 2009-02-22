FSDump Product Overview
=======================

FSDump grew out of an itch which many Zope developers have:
through-the-web development is faster and easier to do, but
causes significant deployment and configuration management
problems.  Through-the-web code cannot (easily) be checked into
CVS, or diffed to show changes, or grepped to find the source
of an error message.

Goals
-----

- The first goal is to ease the burden of getting TTW code
  under version control:  i.e., to make it possible to check
  a representation of the TTW code into CVS, and then to see
  what changes between versions.

- Keep the file-system representations of the TTW objects 
  simple and "natural" (we are explicitly avoiding XML here).

- Future goals might include:

  o Two-way migration (e.g., make changes to dumped items in
    vim/emacs, and then import those changes back into the
    TTW code).

Installation
------------

See the separate `installation directions <INSTALL.html>`_.


Usage
-----

- Use the "Add list" to create a "Dumper" instance in a folder
  (or Product) which contains the TTW code to be dumped.

- Supply an absolute path to a directory on the filesystem
  in which the dumper is to create the files (note that the
  user as whom Zope is running needs write access to this
  directory).  See the `form help <Dumper_editForm.html>`_.

- Click the "Change and Dump" button to do the dump to the
  indicated directory.


Mapping TTW Code to the Filesystem
----------------------------------

See the `mappings documentation <Mappings.html>`_.


Known Issues
------------

- Some types of metadata (``bobobase_modification_time``) won't
  be exported as a property.

- See the `TODO list <TODO.html>`_.
