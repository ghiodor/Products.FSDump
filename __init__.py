import Dumper

def initialize( context ):

    context.registerClass( Dumper.Dumper
                         , constructors= ( ( 'addDumperForm'
                                           , Dumper.addDumperForm
                                           )
                                         , Dumper.addDumper
                                         )
                         , permission= 'Add Dumper'
                         , icon='images/dumper.gif'
                         )
