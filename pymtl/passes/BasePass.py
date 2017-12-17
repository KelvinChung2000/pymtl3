#-------------------------------------------------------------------------
# BasePass
#-------------------------------------------------------------------------

class BasePass(object):

  def __init__( self, debug=False ): # initialize parameters
    self.debug = debug

  def apply( self, m ): # execute pass on model m
    pass
