##############################################################################
#
# Copyright (c) 2001-2004 Zope Corporation. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
import Dumper

def initialize( context ):

    context.registerClass( Dumper.Dumper
                         , constructors= ( ( 'addDumperForm'
                                           , Dumper.addDumperForm
                                           )
                                         , Dumper.addDumper
                                         )
                         , permission= 'Add Dumper'
                         , icon='www/dumper.gif'
                         )

    context.registerHelpTitle( 'FSDump Help' )
    context.registerHelp( directory='help' )
