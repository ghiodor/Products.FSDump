##############################################################################
# 
# Zope Public License (ZPL) Version 1.0
# -------------------------------------
# 
# Copyright (c) Digital Creations.  All rights reserved.
# 
# This license has been certified as Open Source(tm).
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# 1. Redistributions in source code must retain the above copyright
#    notice, this list of conditions, and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions, and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
# 
# 3. Digital Creations requests that attribution be given to Zope
#    in any manner possible. Zope includes a "Powered by Zope"
#    button that is installed by default. While it is not a license
#    violation to remove this button, it is requested that the
#    attribution remain. A significant investment has been put
#    into Zope, and this effort will continue if the Zope community
#    continues to grow. This is one way to assure that growth.
# 
# 4. All advertising materials and documentation mentioning
#    features derived from or use of this software must display
#    the following acknowledgement:
# 
#      "This product includes software developed by Digital Creations
#      for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
#    In the event that the product being advertised includes an
#    intact Zope distribution (with copyright and license included)
#    then this clause is waived.
# 
# 5. Names associated with Zope or Digital Creations must not be used to
#    endorse or promote products derived from this software without
#    prior written permission from Digital Creations.
# 
# 6. Modified redistributions of any form whatsoever must retain
#    the following acknowledgment:
# 
#      "This product includes software developed by Digital Creations
#      for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
#    Intact (re-)distributions of any official Zope release do not
#    require an external acknowledgement.
# 
# 7. Modifications are encouraged but must be packaged separately as
#    patches to official Zope releases.  Distributions that do not
#    clearly separate the patches from the original work must be clearly
#    labeled as unofficial distributions.  Modifications which do not
#    carry the name Zope may be packaged in any form, as long as they
#    conform to all of the clauses above.
# 
# 
# Disclaimer
# 
#   THIS SOFTWARE IS PROVIDED BY DIGITAL CREATIONS ``AS IS'' AND ANY
#   EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#   PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL DIGITAL CREATIONS OR ITS
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
#   USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#   OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
#   OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
#   SUCH DAMAGE.
# 
# 
# This software consists of contributions made by Digital Creations and
# many individuals on behalf of Digital Creations.  Specific
# attributions are listed in the accompanying credits file.
# 
##############################################################################
"""\
This file is an installation script for CMFDecor (ZPT skins).  It's meant
to be used as an External Method.  To use, add an external method to the
root of the CMF Site that you want ZPT skins registered in with the
configuration:

 id: install_decor
 title: Install Decor Skins *optional*
 module name: CMFDecor.Install
 function name: install

Then go to the management screen for the newly added external method
and click the 'Try it' tab.  The install function will execute and give
information about the steps it took to register and install the
ZPT skins into the CMF Site instance. 
"""
from Products.CMFCore.TypesTool import ContentFactoryMetadata
from Products.CMFCore.DirectoryView import addDirectoryViews
from Products.CMFCore.utils import getToolByName
from Products.CMFDecor import cmfdecor_globals

from Acquisition import aq_base
from cStringIO import StringIO
import string

ZPT_SKINS_DIRS = ( 'zpt_content', 'zpt_control', 'zpt_generic', 'zpt_images' )

def install(self):
    " Register the ZPT Skins with portal_skins and friends "
    out = StringIO()
    skinstool = getToolByName(self, 'portal_skins')

    for dir_view in ZPT_SKINS_DIRS:
        if dir_view in skinstool.objectIds():
            skinstool._delObject( dir_view )

    try:
        addDirectoryViews( skinstool, 'skins', cmfdecor_globals )
    except:
        pass
    out.write( "Added CMFDecor directory views to portal_skins\n" )

    #
    #   Add a new skin, 'ZPT', copying 'Basic', if it exists, and then
    #   add our directories only to it.
    #
    if skinstool.getSkinPath( 'ZPT' ) is None:

        path = skinstool.getSkinPath( skinstool.getDefaultSkin() )
        path = map( string.strip, string.split( path,',' ) )
        for zptdir in ZPT_SKINS_DIRS:
            try:
                path.insert( path.index( 'content' ), zptdir )
            except ValueError:
                path.append( zptdir )
                    
        path = string.join( path, ', ' )
        skinstool.addSkinSelection( 'ZPT', path )
        out.write( "Added ZPT skin\n" )
    
    else:
        out.write( "ZPT skin already exists\n" )

    return out.getvalue()
