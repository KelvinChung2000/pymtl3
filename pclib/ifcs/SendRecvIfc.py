#=========================================================================
# SendRecvIfc.py
#=========================================================================
# RTL implementation of en/rdy micro-protocol.
#
# Author: Yanghui Ou
#   Date: Feb 21, 2019

from pymtl import *
from ifcs_utils import enrdy_to_str

#-------------------------------------------------------------------------
# SendRecvIfc
#-------------------------------------------------------------------------

class RecvIfcRTL( Interface ):

  def construct( s, Type ):

    s.msg =  InVPort( Type )
    s.en  =  InVPort( int if Type is int else Bits1 )
    s.rdy = OutVPort( int if Type is int else Bits1 )

  def line_trace( s ):
    return enrdy_to_str( s.msg, s.en, s.rdy )

  def __str__( s ):
    return s.line_trace()

class SendIfcRTL( Interface ):

  def construct( s, Type ):

    s.msg = OutVPort( Type )
    s.en  = OutVPort( int if Type is int else Bits1 )
    s.rdy =  InVPort( int if Type is int else Bits1 )

  def line_trace( s ):
    return enrdy_to_str( s.msg, s.en, s.rdy )

  def __str__( s ):
    return s.line_trace()