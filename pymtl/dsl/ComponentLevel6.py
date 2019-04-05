#=========================================================================
# ComponentLevel6.py
#=========================================================================
# Add method port decorator and clk/reset signals.
#
# Author : Yanghui Ou, Shunning Jiang
#   Date : Feb 24, 2019

from pymtl.datatypes import Bits1
from ComponentLevel5 import ComponentLevel5
from Connectable import CallerPort, CalleePort, Interface, InVPort

#-------------------------------------------------------------------------
# method_port decorator
#-------------------------------------------------------------------------

def generate_guard_decorator_ifcs( name ):
  class GuardedCalleeIfc( Interface ):
    guarded_ifc = True
    def construct( s, method=None, guard=None ):
      s.method = CalleePort( method )
      setattr( s, name, CalleePort( guard ) )
    def __call__( s, *args, **kwargs ):
      return s.method( *args, **kwargs )

  class GuardedCallerIfc( Interface ):
    guarded_ifc = True
    def construct( s ):
      s.method = CallerPort( )
      setattr( s, name, CallerPort() )
    def __call__( s, *args, **kwargs ):
      return s.method( *args, **kwargs )

  def guard_decorator( guard=lambda : True ):
    def real_guard( method ):
      setattr( method, "_guard_method_" + name, guard )
      setattr( method, "_guard_callee_ifc_type_" + name, GuardedCalleeIfc )

      return method
    return real_guard

  return guard_decorator, GuardedCalleeIfc, GuardedCallerIfc

#-------------------------------------------------------------------------
# ComponentLevel6
#-------------------------------------------------------------------------

class ComponentLevel6( ComponentLevel5 ):

  # Override
  def _construct( s ):
    """ We override _construct here to add method binding. Basically
    we do this after the class is constructed but before the construct()
    elaboration happens."""

    if not s._dsl.constructed:

      s.clk   = InVPort( Bits1 )
      s.reset = InVPort( Bits1 )

      kwargs = s._dsl.kwargs.copy()
      if "elaborate" in s._dsl.param_dict:
        kwargs.update( { x: y for x, y in s._dsl.param_dict[ "elaborate" ].iteritems()
                              if x } )

      # The following code handles guarded methods
      def bind_method( method ):
        def _method( *args, **kwargs ):
          return method( s, *args, **kwargs )
        return _method

      for x in dir( s ):
        method = getattr( s, x )
        # We identify guarded methods here
        for y in dir( method ):
          if y.startswith( "_guard_method" ):
            guard = getattr( method, y )
            # This getattr will get the bounded method from ComponentLevel4
            ifc_type = getattr( method, "_guard_callee_ifc_type_" + y[14:] )
            ifc = ifc_type( method, bind_method( guard ) )
            setattr( s, x, ifc )

      # Same as parent class _construct

      s.construct( *s._dsl.args, **kwargs )

      try:
        s.connect( s.clk, s.get_parent_object().clk )
        s.connect( s.reset, s.get_parent_object().reset )
      except AttributeError:
        pass

      if s._dsl.call_kwargs is not None: # s.a = A()( b = s.b )
        s._continue_call_connect()

      s._dsl.constructed = True

  def sim_reset( s ):
    assert s._dsl.elaborate_top is s # assert sim_reset is top

    s.reset = Bits1( 1 )
    s.tick() # This tick propagates the reset signal
    s.tick()
    s.reset = Bits1( 0 )