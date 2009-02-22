FSDump ToDos
============

Planned
-------

- [x] Target .metadata file expected by newer CMF releases.
      (in the ``[Default]`` section);  write ``.objects`` entries into its
      ``[Objects]`` section.

- [x] Map the permission-role map in the ``[Permissions]`` section of the
      companion ``.metadata`` file (XXX this feature not present before
      the switch to ``.metadata``, although it might have mapped to the
      ".security" file supported by CMF 1.3)

- [x] Map local roles in the ``[LocalRoles]`` section of the
      companion ``.metadata`` file (XXX this feature not present before
      the switch to ``.metadata``)

- [x] Write proxy roles to a ``proxy`` property (XXX CMF 1.4 compatibility;
      this is an *ugly* spelling).  Should probably put it into a "prettier"
      spelling, as well, and lobby to change the spelling used in CMF.

- [_] Finish out the typelist for "standard" metatypes:

      * Database connectors

- [_] Make the dumper easier to extend (e.g., by adding *more* TTW code
      to emit FS code ;), or by registering handlers for new metatypes.)

No Way
------

- Integrate with the HelpSystem.

- Introspect ZClass instances to export them using their propertysheets.

