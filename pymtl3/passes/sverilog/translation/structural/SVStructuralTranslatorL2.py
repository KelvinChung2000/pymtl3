#=========================================================================
# SVStructuralTranslatorL2.py
#=========================================================================
"""Provide SystemVerilog structural translator implementation."""
from __future__ import absolute_import, division, print_function

from functools import reduce

from pymtl3.passes.rtlir import RTLIRDataType as rdt
from pymtl3.passes.sverilog.util.utility import make_indent
from pymtl3.passes.translator.structural.StructuralTranslatorL2 import (
    StructuralTranslatorL2,
)

from .SVStructuralTranslatorL1 import SVStructuralTranslatorL1


class SVStructuralTranslatorL2(
    SVStructuralTranslatorL1, StructuralTranslatorL2 ):

  #-----------------------------------------------------------------------
  # Data types
  #-----------------------------------------------------------------------

  def rtlir_tr_packed_array_dtype( s, dtype ):
    sub_dtype = dtype.get_sub_dtype()
    if isinstance( sub_dtype, rdt.Vector ):
      sub_dtype_template = s.rtlir_tr_vector_dtype( sub_dtype )
    elif isinstance( sub_dtype, rdt.Struct ):
      sub_dtype_template = s.rtlir_tr_struct_dtype( sub_dtype )
    else:
      assert False, "unsupported data type {} in packed array!".format(sub_dtype)
    dim_str = reduce(lambda x,y: x+'[{}:0]'.format(y-1), dtype.get_dim_sizes(), '')
    str_list = sub_dtype_template['decl'].split()
    if '[' in str_list[-2]:
      str_list[-2] = dim_str + str_list[-2]
    else:
      str_list = str_list[:-1] + [ dim_str ] + [ str_list[-1] ]
    return {
      'def' : '',
      'decl' : ' '.join( str_list ),
      'ndim' : dtype.get_dim_sizes(),
      'raw_dtype' : dtype
    }

  def rtlir_tr_struct_dtype( s, dtype ):
    dtype_name = dtype.get_name()
    field_decls = []

    for id_, _dtype in dtype.get_all_properties():

      if isinstance( _dtype, rdt.Vector ):
        decl = s.rtlir_tr_vector_dtype( _dtype )['decl'].format(**locals())
      elif isinstance( _dtype, rdt.PackedArray ):
        decl = s.rtlir_tr_packed_array_dtype( _dtype )['decl'].format(**locals())
      elif isinstance( _dtype, rdt.Struct ):
        decl = s.rtlir_tr_struct_dtype( _dtype )['decl'].format(**locals())
      else:
        assert False, \
        'unrecoganized field type {} of struct {}!'.format( _dtype, dtype_name )
      field_decls.append( decl + ';' )

    make_indent( field_decls, 1 )
    field_decl = '\n'.join( field_decls )

    file_info = dtype.get_file_info()

    return {
      'def' : \
"""\
typedef struct packed {{
{field_decl}
}} {dtype_name};
""".format( **locals() ),
      'decl' : '{dtype_name} {{id_}}'.format( **locals() ),
      'raw_dtype' : dtype
    }

  #-----------------------------------------------------------------------
  # Signal oeprations
  #-----------------------------------------------------------------------

  def rtlir_tr_packed_index( s, base_signal, index ):
    return '{base_signal}[{index}]'.format( **locals() )

  def rtlir_tr_struct_attr( s, base_signal, attr ):
    return '{base_signal}.{attr}'.format( **locals() )
