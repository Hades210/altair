"""
Utility routines
"""
import warnings

import pandas as pd
import traitlets as T


TYPECODE_MAP = {'ordinal': 'O',
                'nominal': 'N',
                'quantitative': 'Q',
                'temporal': 'T'}

INV_TYPECODE_MAP = {v:k for k,v in TYPECODE_MAP.items()}

TYPE_ABBR = TYPECODE_MAP.values()


def parse_shorthand(sh):
    """
    Altair accepts a shorthand expression for aggregation, field, and type.

    Parse strings of the form

    - "col_name"
    - "col_name:O"
    - "avg(col_name)"
    - "avg(col_name):O"

    Parameters
    ----------
    sh: str
    """
    # TODO: use an actual parser for this?

    # extract type code
    L = sh.split(':')
    sh0 = L[0].strip()
    if len(L) == 1:
        typ = None
    elif len(L) == 2:
        typ = L[1].strip()
    else:
        raise ValueError('Multiple colons not valid in data specification:'
                         '{0}'.format(sh))

    # find aggregate
    if not sh0.endswith(')'):
        agg, field = None, sh0
    else:
        L = sh0[:-1].split('(')
        if len(L) == 2:
            agg, field = L
        else:
            raise ValueError("Unmatched parentheses")

    # validate & store type code
    valid_types = list(TYPECODE_MAP.keys()) + list(TYPECODE_MAP.values())
    if typ is not None and typ not in valid_types:
        raise ValueError('Invalid type code: "{0}".\n'
                         'Valid values are {1}'.format(typ, valid_types))
    typ = TYPECODE_MAP.get(typ, typ)

    # encode and return the results
    result = {}
    if typ:
        result['type'] = typ
    if agg:
        result['aggregate'] = agg
    if field:
        result['field'] = field
    return result


def construct_shorthand(field=None, aggregate=None, type=None):
    if field is None:
        return ''

    sh = field

    if aggregate is not None:
        sh = '{0}({1})'.format(aggregate, sh)

    if type is not None:
        type = TYPECODE_MAP.get(type, type)
        if type not in TYPE_ABBR:
            raise ValueError('Unrecognized Type: {0}'.format(typ))
        sh = '{0}:{1}'.format(sh, type)

    return sh


def infer_vegalite_type(data, name=None):
    """
    From an array-like input, infer the correct vega typecode
    ('O', 'N', 'Q', or 'T')

    Parameters
    ----------
    data: Numpy array or Pandas Series
    field: str column name
    """
    # See if we can read the type from the name
    if name is not None:
        parsed = parse_shorthand(field)
        if parsed.get('type'):
            return parsed['type']

    # Otherwise, infer based on the dtype of the input
    typ = pd.lib.infer_dtype(data)

    # TODO: Once this returns 'O', please update test_select_x and test_select_y in test_api.py

    if typ in ['floating', 'mixed-integer-float', 'integer',
               'mixed-integer', 'complex']:
        typecode = 'quantitative'
    elif typ in ['string', 'bytes', 'categorical', 'boolean', 'mixed', 'unicode']:
        typecode = 'nominal'
    elif typ in ['datetime', 'datetime64', 'timedelta',
                 'timedelta64', 'date', 'time', 'period']:
        typecode = 'temporal'
    else:
        warnings.warn("I don't know how to infer vegalite type from '{0}'.  "
                      "Defaulting to nominal.".format(typ))
        typecode = 'nominal'

    return TYPECODE_MAP[typecode]


def sanitize_dataframe(df):
    """Sanitize a DataFrame to prepare it for serialization.

    * Make a copy
    * Raise ValueError is it has a hierarchical index.
    * Convert categoricals to strings.
    * Convert np.int dtypes to Python int objects
    * Convert DateTime dtypes into appropriate string representations
    """
    import pandas as pd
    import numpy as np
    df = df.copy()

    if type(df.index) == pd.core.index.MultiIndex:
        raise ValueError('Hierarchical indices not supported')
    if type(df.columns) == pd.core.index.MultiIndex:
        raise ValueError('Hierarchical indices not supported')

    for col_name, dtype in df.dtypes.iteritems():
        if str(dtype) == 'category':
            # XXXX: work around bug in to_json for categorical types
            # https://github.com/pydata/pandas/issues/10778
            df[col_name] = df[col_name].astype(str)
        elif np.issubdtype(dtype, np.integer):
            df[col_name] = np.array(list(map(int, df[col_name])), dtype=object)
        elif str(dtype) == 'datetime64[ns]':
            # this is the format used in Vega-Lite example area.json
            to_str = lambda x: x.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            df[col_name] = df[col_name].apply(to_str)
    return df
    