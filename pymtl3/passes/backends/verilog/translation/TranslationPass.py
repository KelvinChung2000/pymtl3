#=========================================================================
# TranslationPass.py
#=========================================================================
# Author : Peitian Pan
# Date   : March 12, 2019
"""Translate a PyMTL component hierarhcy into SystemVerilog source code."""

import filecmp
import os

from pymtl3 import MetadataKey
from pymtl3.passes.BasePass import BasePass

from .VTranslator import VTranslator


def mk_TranslationPass( _VTranslator ):

  class _TranslationPass( BasePass ):

    # Translation pass input pass data

    enable                = MetadataKey()
    explicit_file_name    = MetadataKey()
    explicit_module_name  = MetadataKey()
    no_synthesis          = MetadataKey()
    no_synthesis_no_clk   = MetadataKey()
    no_synthesis_no_reset = MetadataKey()

    # Translation pass output pass data

    translate_config      = MetadataKey()

    is_same               = MetadataKey()
    translator            = MetadataKey()
    translated            = MetadataKey()
    translated_filename   = MetadataKey()
    translated_top_module = MetadataKey()

    def __call__( s, top ):
      s.top = top
      s.translator = _VTranslator( s.top )
      s.traverse_hierarchy( top )

    def get_translation_config( s ):
      from pymtl3.passes.backends.verilog.translation.TranslationConfigs \
          import TranslationConfigs
      return TranslationConfigs

    def gen_tr_cfgs( s, m ):
      tr_cfgs = {}

      def traverse( m ):
        nonlocal tr_cfgs
        tr_cfgs[m] = s.get_translation_config()( m )
        for _m in m.get_child_components(repr):
          traverse( _m )

      traverse( m )
      return tr_cfgs

    def traverse_hierarchy( s, m ):
      c = s.__class__

      if m.has_metadata( c.enable ) and m.get_metadata( c.enable ):
        m.set_metadata( c.translate_config, s.gen_tr_cfgs(m) )
        s.translator.translate( m, m.get_metadata( c.translate_config ) )

        module_name = s.translator._top_module_full_name

        if m.has_metadata( c.explicit_file_name ) and \
           m.get_metadata( c.explicit_file_name ):
          fname = m.get_metadata( c.explicit_file_name )
          if '.v' in fname:
            filename = fname.split('.v')[0]
          elif '.sv' in fname:
            filename = fname.split('.sv')[0]
          else:
            filename = fname
        else:
          filename = f"{module_name}__pickled"

        output_file = filename + '.v'
        temporary_file = filename + '.v.tmp'

        # First write the file to a temporary file
        is_same = False
        with open( temporary_file, 'w' ) as output:
          output.write( s.translator.hierarchy.src )
          output.flush()
          os.fsync( output )
          output.close()

        # `is_same` is set if there exists a file that has the same filename as
        # `output_file`, and that file is the same as the temporary file
        if ( os.path.exists(output_file) ):
          is_same = filecmp.cmp( temporary_file, output_file )

        # Rename the temporary file to the output file
        os.rename( temporary_file, output_file )

        # Expose some attributes about the translation process
        m.set_metadata( c.is_same,               is_same      )
        m.set_metadata( c.translator,            s.translator )
        m.set_metadata( c.translated,            True         )
        m.set_metadata( c.translated_filename,   output_file  )
        m.set_metadata( c.translated_top_module, module_name  )

      else:
        for child in m.get_child_components(repr):
          s.traverse_hierarchy( child )

  return _TranslationPass

TranslationPass = mk_TranslationPass( VTranslator )
