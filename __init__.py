##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
# All Rights Reserved.
# 
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
# 
##############################################################################

__doc__='''Package wrapper for Queued Catalogs

$Id$'''
__version__='$$'[11:-2]

# Placeholder for Zope Product data
misc_ = {}

from QueueCatalog import QueueCatalog
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

manage_addQueueCatalogForm = PageTemplateFile(
    'add.pt', globals(), __name__='manage_addQueueCatalogForm')


def manage_addQueueCatalog(self, id, REQUEST=None):
    "Add a Catalog Queue"
    ob = QueueCatalog()
    ob.id = id
    self._setObject(id, ob)
    if REQUEST is not None:

        try:
            u = self.DestinationURL()
        except AttributeError:
            u = REQUEST['URL1']

        REQUEST.RESPONSE.redirect(u+'/manage_main')

def initialize(context):
    context.registerClass(
        QueueCatalog,
        permission='Add ZCatalogs',
        constructors=(manage_addQueueCatalogForm, manage_addQueueCatalog, ),
        icon='QueueCatalog.gif',
        )
    #context.registerHelp()
    #context.registerHelpTitle('Zope Help')
