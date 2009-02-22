Installing FSDump
=================

1. Unpack the tarball into a temporary location.  E.g.::

    $ cd /tmp
    $ tar xzf FSDump-0.9.2.tar.gz

2. Copy the FSDump directory from that location into the 'Products'
   directory of your Zope application server instance.  E.g.::

    $ cd FSDump-0.9.2
    $ cp -r FSDump /var/zope/Products/

3. Restart Zope.
