from pathlib import Path
from nwb_extensions_smithy.metadata import MetaData
import sys

def main():
    path = Path(sys.argv[1]).resolve().as_posix()
    meta = MetaData(path)
    print(meta.name())

if __name__ == '__main__':
    main()
