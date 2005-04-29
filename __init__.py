""" FSDump product intialization

$Id$
"""
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
