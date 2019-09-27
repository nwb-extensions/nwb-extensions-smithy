#!/usr/bin/env python
from setuptools import setup
import versioneer


def main():
    skw = dict(
        name="nwb-extensions-smithy",
        version=versioneer.get_version(),
        description="A package to create extensions for NWB, and automate "
        "their building with CI tools on Linux, macOS, and Windows.",
        author="Ryan Ly",
        author_email="rly@lbl.gov",
        url="https://github.com/nwb-extensions/nwb-extensions-smithy",
        entry_points=dict(
            console_scripts=[
                # "feedstocks = nwb_extensions_smithy.feedstocks:main",
                "nwb-extensions-smithy = nwb_extensions_smithy.cli:main",
            ]
        ),
        include_package_data=True,
        packages=["nwb_extensions_smithy"],
        # As nwb-extensions-smithy has resources as part of the codebase, it is
        # not zip-safe.
        zip_safe=False,
        cmdclass=versioneer.get_cmdclass(),
    )
    setup(**skw)


if __name__ == "__main__":
    main()
