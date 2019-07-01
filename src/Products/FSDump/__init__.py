""" FSDump product intialization

$Id: __init__.py 105463 2009-11-03 14:52:27Z tseaver $
"""
from Products.FSDump.Dumper import initialize


"""def initialize(context):

    context.registerClass(Dumper.Dumper,
                           constructors= (Dumper.manage_addFSDumpForm,
                                          Dumper.manage_addFSDump),
                           permission= 'Add Dumper',
                           icon='www/dumper.gif'
   )
"""
