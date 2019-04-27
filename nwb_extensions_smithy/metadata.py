import os.path
import glob
import ruamel.yaml as yaml
from warnings import warn

from conda_build.metadata import stringify_numbers, sanitize, check_bad_chrs
from conda_build.license_family import ensure_valid_license_family

# Adapted from conda_build.metadata.py

# TODO specify these
FIELDS = {
    'package': {'name', 'version'},
    'source': {'fn', 'url', 'md5', 'sha1', 'sha256', 'path',
               'git_url', 'git_tag', 'git_branch', 'git_rev', 'git_depth',
               },
    'build': {},
    'test': {},
    'about': {'home', 'dev_url', 'doc_url', 'doc_source_url', 'license_url',  # these are URLs
              'license', 'summary', 'description', 'license_family',  # text
              'identifiers', 'tags', 'keywords',   # lists
              'license_file', 'readme',   # paths in source tree
              },
}


class MetaData:
    def __init__(self, path):
        if os.path.isfile(path):
            self.meta_path = path
            self.path = os.path.dirname(path)
        else:
            self.meta_path = find_metadata(path)
            self.path = os.path.dirname(self.meta_path)

        self.meta = {}
        if self.meta_path:
            self.meta = load_file(self.meta_path)


    def name(self):
        res = self.meta.get('package', {}).get('name', '')
        if not res:
            raise RuntimeError('package/name missing in: %r' % self.meta_path)
        res = str(res)
        if res != res.lower():
            raise RuntimeError('package/name must be lowercase, got: %r' % res)
        check_bad_chrs(res, 'package/name')
        return res



def find_metadata(path):
    '''
    Recurse through a folder, locating ndx-meta.yaml, and returns path to file.
    Raises warning if a base level ndx-meta.yaml and other supplemental ones are
    found, and then uses the base level file.
    Raises error if more than one is found and none are in the base directory.
    '''
    meta_name = 'ndx-meta.yaml';
    if os.path.isfile(path) and os.path.basename(path) == meta_name:
        return os.path.dirname(path)

    results = [f for f in glob.iglob(os.path.join(path, '**', meta_name), recursive=True)]

    if len(results) > 1:
        base_recipe = os.path.join(path, meta_name)
        if base_recipe in results:
            warn(f'Multiple {meta_name} files found. '
                 f'The {meta_name} file in the base directory will be used.')
            results = [base_recipe]
        else:
            raise IOError(f'No {meta_name} found in base directory, and '
                          f'more than one {meta_name} files found in {path}.')
    elif not results:
        raise IOError(f'No {meta_name} files found in {path}.')
    return results[0]


def load_file(path):
    ''' Read yaml from a yaml file '''
    data = None
    with open(path, 'r') as f:
        try:
            # TODO make sure this works with different encodings...
            data = yaml.load(f.read(), Loader=yaml.Loader)
        except yaml.error.YAMLError as e:
            raise RuntimeError(f'Cannot parse metadata in file {path}.')
    return clean(data)


def load_stream(stream):
    ''' Read yaml from a data stream '''
    data = None
    try:
        # TODO make sure this works with different encodings...
        data = yaml.load(stream, Loader=yaml.Loader)
    except yaml.error.YAMLError as e:
        raise RuntimeError(f'Cannot parse metadata in file {path}.')
    return clean(data)


def clean(data):
    ''' Check a few things on the yaml file and sanitize the data '''
    if data is None:
        raise RuntimeError(f'There is no data in file {path}.')
    # ensure the known fields are dicts
    for field in FIELDS:
        if field not in data:
            continue
        if not isinstance(data[field], dict):
            raise RuntimeError('The %s field should be a dict, not %s in file %s.' %
                               (field, data[field].__class__.__name__, path))

    ensure_valid_license_family(data)
    # clean git spec in source, and turns package/build version into string
    return sanitize(data)
