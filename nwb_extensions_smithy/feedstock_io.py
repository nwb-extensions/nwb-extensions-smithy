from contextlib import contextmanager
import io
import os
import shutil
import stat


def get_repo(path, search_parent_directories=True):
    repo = None
    try:
        import git

        repo = git.Repo(
            path, search_parent_directories=search_parent_directories
        )
    except ImportError:
        pass
    except git.InvalidGitRepositoryError:
        pass

    return repo


def set_exe_file(filename, set_exe=True):
    IXALL = stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR

    repo = get_repo(filename)
    if repo:
        mode = "+x" if set_exe else "-x"
        repo.git.execute(
            ["git", "update-index", "--chmod=%s" % mode, filename]
        )

    mode = os.stat(filename).st_mode
    if set_exe:
        mode |= IXALL
    else:
        mode -= mode & IXALL
    os.chmod(filename, mode)


@contextmanager
def write_file(filename):
    dirname = os.path.dirname(filename)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)

    with io.open(filename, "w", encoding="utf-8", newline="\n") as fh:
        yield fh

    repo = get_repo(filename)
    if repo:
        repo.index.add([filename])


def touch_file(filename):
    with write_file(filename) as fh:
        fh.write("")


def remove_file_or_dir(filename):
    if not os.path.isdir(filename):
        return remove_file(filename)

    repo = get_repo(filename)
    if repo:
        repo.index.remove([filename], r=True)
    shutil.rmtree(filename)


def remove_file(filename):
    touch_file(filename)

    repo = get_repo(filename)
    if repo:
        repo.index.remove([filename])

    os.remove(filename)

    dirname = os.path.dirname(filename)
    if dirname and not os.listdir(dirname):
        os.removedirs(dirname)


def copy_file(src, dst):
    """
    Try to copy utf-8 text files line-by-line to avoid getting CRLF characters added on Windows.

    If the file fails to be decoded with utf-8, we revert to a regular copy.
    """
    try:
        with io.open(src, "r", encoding="utf-8") as fh_src:
            with io.open(dst, "w", encoding="utf-8", newline="\n") as fh_dst:
                for line in fh_src:
                    fh_dst.write(line)
    except UnicodeDecodeError:
        # Leave any other files alone.
        shutil.copy(src, dst)

    shutil.copymode(src, dst)

    repo = get_repo(dst)
    if repo:
        repo.index.add([dst])


def copytree(src, dst, ignore=(), root_dst=None):
    """This emulates shutil.copytree, but does so with our git file tracking, so that the new files
    are added to the repo"""
    if root_dst is None:
        root_dst = dst
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.relpath(d, root_dst) in ignore:
            continue
        elif os.path.isdir(s):
            if not os.path.exists(d):
                os.makedirs(d)
            copytree(s, d, ignore, root_dst=root_dst)
        else:
            copy_file(s, d)
