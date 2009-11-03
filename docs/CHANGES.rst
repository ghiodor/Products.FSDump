FSDump Changelog
================

0.9.5 (2009-11-03)
------------------

- Removed broken HelpSys registrations.

- Fixed the version number used in making the sdist.


0.9.4 (2009-02-22)
------------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/0.9.4

- Repackaged as a Python egg.

- Converted docs to ReStructured text.

- Moved from CVS to SVN.


0.9.3 (2006-12-20)
------------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_9_3

- Applied patch from Damine Baty, fixing the output of dumping ZSQLMethods
  to match the format used by CMF's FSZSQLMethods.
  
- Applied patch from Alejo Roda, adding a handler for Formulator forms.

- Applied patch from Willi Langenburger, adding a handler for ZWikiPage
  objects.


0.9.2 (2005-08-09)
-------------------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_9_2

- CVS tag:  ``FSDump-0_9_2``

- Reverted ``handler_overrides`` brownbag


0.9.1 (2005-08-09)
------------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_9_1

- CVS tag:  ``FSDump-0_9_1``

- Added argument to Dumper factory to allow caller to supply handler
  overrides.

- Applied patch from Sam Brauer, addressing the following issues:

  * Proxy roles and security settings weren't being written to
    the ``.metadata`` file.

  * The ``[Default]`` section should be named ``[default]``.

  * The property-type extensions confuse CMF's FilesystemDirectoryView
    (the patch removes the ``:string`` for string properties;  others
    are likely still broken).

  
0.9 (2005-04-29)
----------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_9

- CVS tag:  ``FSDump-0_9``

- Merged Andy Fundinger's work, adding handlers for the following
  CMFFormController meta_types:

  * ControllerPythonScript

  * ControllerValidator

  * ControllerPageTemplates

- Fix missing import of ConflictError (thanks to Willi Langenburger
  for the patch).

- Applied a patch from Willi Langenburger to permit use of a dumper
  in the root of the Zope instance.


0.8.1 (2004-12-09)
------------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_8_1

- CVS tag:  ``FSDump-0_8_1``

- Repackaged to nest the actual products directory inside a version-
  qualified wrapper directory;  added an INSTALL.txt in the wrapper.


0.8 (2004-10-13)
----------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_8

- CVS tag:  ``FSDump-0_8``

- Applied patch from Zope collector #1463 to make dumped SQL methods
  fit better with CMF's FSSQLMethod representation.


0.7 (2004-05-17)
----------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_7

- CVS tag:  ``FSDump-0_7``

- Added knob to force use of single ``.metadata`` file, rather than
  multiples (CMF 1.4 compatibility).

- Migrated ZMI to use PageTemplates.

- Bug:  when synthesizing a file extension, Dumper didn't include the
  synthesized extension in the name of the "companion" properties file.


0.6 (2001-08-09)
----------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_6

- CVS tag:  ``FSDump-0_6``

- Add handlers for:

  - PageTemplate


0.5 (2001-08-03)
----------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_5

- CVS tag:  ``FSDump-0_5``

- Add handlers for:

  - PythonScript


0.4 (2001-06-18)
----------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_4

- CVS tag:  ``FSDump-0_4``

- Conform to the "Finished Project Guidelines",
  http://dev.zope.org/Wikis/DevSite/Proposals/FinishedProductGuidelines

- Added HelpSystem stuff.

- Moved to use declarative security.


0.3 (2001-01-06)
----------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_3

- No CVS tag?

- Dump ZClass icon.

- Add handlers for:

  * Wizards

  * Wizard Pages


0.2 (2000-11-19)
----------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_2

- CVS tag:  ``FSDump-0_2``

- Add handlers for:

  * ZClasses

  * ZClass property sheets

  * TTW Permissions

  * TTW Factories


- Fix unixism in ``Dumper._setFSPath()`` -- thanks Craig! (cba@mediaone.net)

0.1 (2000-11-16)
----------------

- SVN:  http://svn.zope.org/Products.FSDump/tags/FSDump-0_1

- CVS tag:  ``FSDump-0_1``

- Initial release
