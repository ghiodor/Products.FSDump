""" FSDump product intialization

$Id$
"""
import Dumper

def initialize(context):
    context.registerClass(
        Dumper.Dumper,
        constructors=(Dumper.manage_addDumperForm,
                      Dumper.manage_addDumper),
        permission='Add Dumper',
        icon='www/dumper.gif'
    )
