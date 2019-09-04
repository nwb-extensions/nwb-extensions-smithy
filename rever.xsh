import os

$PROJECT = $GITHUB_REPO = 'nwb-extensions-smithy'
$GITHUB_ORG = 'nwb-extensions'

$ACTIVITIES = ['changelog', 'tag', 'push_tag', 'ghrelease']

$CHANGELOG_FILENAME = 'CHANGELOG.rst'
$CHANGELOG_TEMPLATE = 'TEMPLATE.rst'

def sdist_asset():
    fname = os.path.join('dist', 'nwb-extensions-smithy-' + $VERSION + '.tar.gz')
    print('Creating sdist tarball ' + fname)
    ![python setup.py sdist]
    return fname

$TAG_TEMPLATE = $GHRELEASE_NAME = 'v$VERSION'
$GHRELEASE_ASSETS = [sdist_asset]
$CONDA_FORGE_SOURCE_URL = ('https://github.com/nwb-extensions/nwb-extensions-smithy/releases/'
                           'download/v$VERSION/nwb-extensions-smithy-$VERSION.tar.gz')
