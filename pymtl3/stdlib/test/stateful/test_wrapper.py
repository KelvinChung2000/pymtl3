#=========================================================================
# test_wrapper
#=========================================================================
# Wrappers for testing rtl model.
#
# Author : Yixiao Zhang
#   Date : May 20, 2019

from __future__ import absolute_import, division, print_function

import copy
import inspect
import linecache

import attr
from pymtl3 import *
from pymtl3.dsl.ComponentLevel6 import ComponentLevel6


#-------------------------------------------------------------------------
# Method
#-------------------------------------------------------------------------
@attr.s()
class Method( object ):
  method_name = attr.ib()
  args = attr.ib( default={} )
  rets = attr.ib( default={} )


#-------------------------------------------------------------------------
# rename
#-------------------------------------------------------------------------
def rename( name ):

  def wrap( f ):
    f.__name__ = name
    return f

  return wrap


#-------------------------------------------------------------------------
# inspect_rtl
#-------------------------------------------------------------------------
def inspect_rtl( rtl ):
  method_specs = {}

  for method, ifc in inspect.getmembers( rtl ):
    args = {}
    rets = {}
    if isinstance( ifc, Interface ):
      for name, port in inspect.getmembers( ifc ):
        if name == 'en' or name == 'rdy':
          continue
        if isinstance( port, InPort ):
          args[ name ] = port._dsl.Type
        if isinstance( port, OutPort ):
          rets[ name ] = port._dsl.Type

      method_specs[ method ] = Method(
          method_name=method, args=args, rets=rets )
  return method_specs


#-------------------------------------------------------------------------
# gen_adapter
#-------------------------------------------------------------------------
def gen_adapter( rtl, method_spec ):
  initialize_args = ""
  update_args = ""
  assign_args = ""

  for arg in method_spec.args:
    initialize_args += """
    s.{name}_{arg} = 0
""".format(
        arg=arg, name=method_spec.method_name )

    update_args += """
      s.{name}_rtl.{arg} = s.{name}_{arg}
""".format(
        arg=arg, name=method_spec.method_name )

    assign_args += """
    s.{name}_{arg} = {arg}
""".format(
        arg=arg, name=method_spec.method_name )

  if method_spec.rets:
    # has ret values
    update_rets = ""
    initialize_rets = ""

    for ret in method_spec.rets:
      update_rets += """
      s.{name}_{ret} = s.{name}_rtl.{ret}
""".format(
          ret=ret, name=method_spec.method_name )

      initialize_rets += """
    s.{name}_{ret} = 0
""".format(
          ret=ret, name=method_spec.method_name )

    rets = ",".join([
        "s.{name}_{ret}".format( name=method_spec.method_name, ret=ret )
        for ret in method_spec.rets.keys()
    ] )

    # template for generated adapter
    # three upblk: args + call, rdy, ret
    tmpl = """
class RTL2CL( Component ):

  def construct( s, {name} ):

    {name}_rtl = copy.deepcopy( {name} )
    {name}_rtl._dsl.constructed = False
    s.{name}_rtl = {name}_rtl.inverse()

    s.{name}_called = False
    s.{name}_rdy = False
{initialize_args}
{initialize_rets}

    @s.update
    def update_{name}_adapter():
      s.{name}_rtl.en = Bits1( 1 ) if s.{name}_called else Bits1( 0 )
      s.{name}_called = False
{update_args}

    @s.update
    def update_{name}_adapter_rdy():
      s.{name}_rdy = True if s.{name}_rtl.rdy else False

    @s.update
    def update_{name}_adapter_ret():
{update_rets}

    s.add_constraints(
        U( update_{name}_adapter_ret ) < M( s.{name} ),
        U( update_{name}_adapter_rdy ) < M( s.{name} ),
        U( update_{name}_adapter ) < RD( s.{name}_rtl.en ),
        M( s.{name} ) < U( update_{name}_adapter ) )

  @non_blocking( lambda s: s.{name}_rdy )
  def {name}( s, {args} ):
    s.{name}_called = True
{assign_args}
    return {rets}
""".format(
        name=method_spec.method_name,
        args=",".join( method_spec.args.keys() ),
        initialize_args=initialize_args,
        assign_args=assign_args,
        update_args=update_args,
        rets=rets,
        update_rets=update_rets,
        initialize_rets=initialize_rets )

  else:
    # no ret values
    tmpl = """
class RTL2CL( Component ):

  def construct( s, {name} ):

    {name}_rtl = copy.deepcopy( {name} )
    {name}_rtl._dsl.constructed = False
    s.{name}_rtl = {name}_rtl.inverse()

    s.{name}_called = False
    s.{name}_rdy = False
{initialize_args}

    @s.update
    def update_{name}_adapter():
      s.{name}_rtl.en = Bits1( 1 ) if s.{name}_called else Bits1( 0 )
      s.{name}_called = False
{update_args}

    @s.update
    def update_{name}_adapter_rdy():
      s.{name}_rdy = True if s.{name}_rtl.rdy else False

    s.add_constraints(
        U( update_{name}_adapter_rdy ) < M( s.{name} ),
        U( update_{name}_adapter ) < RD( s.{name}_rtl.en ),
        M( s.{name} ) < U( update_{name}_adapter ) )

  @non_blocking( lambda s: s.{name}_rdy )
  def {name}( s, {args} ):
    s.{name}_called = True
{assign_args}
""".format(
        name=method_spec.method_name,
        args=",".join( method_spec.args.keys() ),
        initialize_args=initialize_args,
        assign_args=assign_args,
        update_args=update_args )

  # Compile
  # FIXME: add compiled code to linecache to make inspect source code work
  filename = '<add-to-line-cache>'
  lcs = locals().update({
      "Component": Component,
      "non_blocking": non_blocking
  } )
  exec ( compile( tmpl, filename, 'exec' ), globals() )
  lines = [ line + '\n' for line in tmpl.splitlines() ]
  linecache.cache[ filename ] = ( len( tmpl ), None, lines, filename )

  RTL2CL.__name__ = method_spec.method_name + "RTL2CL"
  return RTL2CL


#-------------------------------------------------------------------------
# RTL2CLWrapper
#-------------------------------------------------------------------------
class RTL2CLWrapper( Component ):

  def __init__( s, rtl_model ):
    super( RTL2CLWrapper, s ).__init__()

    s.model_name = type( rtl_model ).__name__

  def construct( s, rtl_model ):
    """Create adapter & add top-level method for each ifc in rtl_model
    """

    s.model = rtl_model

    s.method_specs = inspect_rtl( s.model )

    # Add adapters
    for method_name, method_spec in s.method_specs.iteritems():
      s._gen_adapter( method_spec )

    ComponentLevel6._handle_decorated_methods( s )

  def _gen_adapter( s, method_spec ):
    name = method_spec.method_name
    RTL2CL = gen_adapter( s.model.__dict__[ name ], method_spec )

    tmpl = """
s.{name}_adapter = RTL2CL( s.model.{name} )
s.{name} = NonBlockingCalleeIfc()
s.connect( s.{name}, s.{name}_adapter.{name} )
s.connect( s.{name}_adapter.{name}_rtl, s.model.{name} )
""".format( name=name )

    lcs = locals().update({ "NonBlockingCalleeIfc": NonBlockingCalleeIfc} )
    exec ( compile( tmpl, "<string>", 'exec' ), lcs )

  def line_trace( s ):
    return s.model.line_trace()
