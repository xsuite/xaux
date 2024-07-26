"""
This package is an attempt to make file reading/writing (possibly concurrent) more reliable.

Last update 23/03/2024 - F.F. Van der Veken
"""

import atexit
import datetime
import hashlib
import io
import os
import random
import time
import json

from .fs import FsPath, EosPath
from .fs.temp import _tempdir
from .tools import ranID


protected_open = {}

def exit_handler():
    """This handles cleaning of potential leftover lockfiles."""
    for file in protected_open.values():
        file.release(pop=False)
    _tempdir.cleanup()
atexit.register(exit_handler)


def get_hash(filename, size=128):
    """Get a fast hash of a file, in chunks of 'size' (in kb)"""
    h  = hashlib.blake2b()
    b  = bytearray(size*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


# TODO: there is some issue with the timestamps. Was this really a file
#       corruption, or is this an OS issue that we don't care about?
# TODO: no stats on EOS files
def get_fstat(filename):
    stats = FsPath(filename).stat()
    return {
                'n_sequence_fields': int(stats.n_sequence_fields),
                'n_unnamed_fields':  int(stats.n_unnamed_fields),
                'st_mode':           int(stats.st_mode),
                'st_ino':            int(stats.st_ino),
                'st_dev':            int(stats.st_dev),
                'st_uid':            int(stats.st_uid),
                'st_gid':            int(stats.st_gid),
                'st_size':           int(stats.st_size),
                'st_mtime_ns':       int(stats.st_mtime_ns),
                'st_ctime_ns':       int(stats.st_ctime_ns),
            }


class ProtectFile:
    """A wrapper around a file pointer, protecting it with a lockfile.

    Use
    ---
    It is meant to be used inside a context, where the entering and leaving of a
    context ensures file protection. The moment the object is instantiated, a
    lockfile is generated (which is destroyed after leaving the context). Attempts
    to access the file will be postponed as long as a lockfile exists. Furthermore,
    while in the context, file operations are done on a temporary file, that is
    only moved back when leaving the context.

    The reason to lock read access as well is that we might work with immutable
    files. The following scenario might happen: a file is read by process 1, some
    calculations are done by process 1, the file is read by process 2, and the
    result of the calculations is written by process 1. Now process 2 is working
    on an outdated version of the file. Hence the full process should be locked in
    one go: reading, manipulating/calculating, and writing.

    An important caveat is that, after the manipulation/calculation, the file
    contents have to be wiped before writing, otherwise the contents will be
    appended (as the file pointer is still at the end of the file after reading it
    in). Unless of course that is the intended result. Wiping the file can be
    achieved with the built-in truncate() and seek() methods.

    Attributes
    ----------
    file       : pathlib.Path
        The path to the file to be protected.
    lockfile   : pathlib.Path
        The path to the lockfile.
    tempfile   : pathlib.Path
        The path to a temporary file which will accumulate all writes until the
        ProtectFile object is destroyed, at which point the temporary file will
        replace the original file. Not used when a ProtectFile object is
        instantiated in read-only mode ('r' or 'rb').

    Examples
    --------
    Reading in a file (while making sure it is not written to by another process):

    >>> from xaux import ProtectFile
    >>> with ProtectFile('thebook.txt', 'r', wait=1) as pf:
    >>>    text = pf.read()

    Reading and appending to a file:

    >>> from xaux import ProtectFile
    >>> with ProtectFile('thebook.txt', 'r+', wait=1) as pf:
    >>>    text = pf.read()
    >>>    pf.write("This string will be added at the end of the file, \
    ...               however, it won't be added to the 'text' variable")

    Reading and updating a JSON file:

    >>> import json
    >>> from xaux import ProtectFile
    >>> with ProtectFile(info.json, 'r+', wait=1) as pf:
    >>>     meta = json.load(pf)
    >>>     meta.update({'author': 'Emperor Claudius'})
    >>>     pf.truncate(0)          # Delete file contents (to avoid appending)
    >>>     pf.seek(0)              # Move file pointer to start of file
    >>>     json.dump(meta, pf, indent=2, sort_keys=False))

    Reading and updating a Parquet file:

    >>> import pandas as pd
    >>> from xaux import ProtectFile
    >>> with ProtectFile(mydata.parquet, 'r+b', wait=1) as pf:
    >>>     data = pd.read_parquet(pf)
    >>>     data['x'] += 5
    >>>     pf.truncate(0)          # Delete file contents (to avoid appending)
    >>>     pf.seek(0)              # Move file pointer to start of file
    >>>     data.to_parquet(pf, index=True)
    """

    # Use debug flag below to inspect steps in file IO
    _debug = False
    _testing = False


    def __init__(self, *args, **kwargs):
        """A ProtectFile object, to be used only in a context.

        Parameters
        ---------
        wait : float, default 1
            When a file is locked, the time to wait in seconds before trying to
            access it again.
        use_temporary : bool, default True
            Whether or not to perform writing operations on a temporary file.
            Ignored when the file is read-only.
        check_hash : bool, default True
            Whether or not to verify by hash that the file did not change during
            the lock.
        max_lock_time : float, default None
            If provided, it will write the maximum runtime in seconds inside the
            lockfile. This is to avoid crashed accesses locking the file forever.

        Additionally, the following parameters are inherited from open():
            'file', 'mode', 'buffering', 'encoding', 'errors', 'newline', 'closefd', 'opener'
        """

        # File variables
        # ==============
        # self._file:   path to the file to the protected file
        # self._lock:   path to the lockfile
        # self._temp:   path to the temporary file on which write operations are applied
        # self._fd:     file pointer to the main file
        #               (self._file if readonly, self._temp if writing)

        argnames_open = ['file', 'mode', 'buffering', 'encoding', 'errors', 'newline',
                         'closefd', 'opener']
        arg = dict(zip(argnames_open, args))
        arg.update(kwargs)

        # Using a temporary file to write to
        self._use_temporary = arg.pop('use_temporary', True)
        self._check_hash = arg.pop('check_hash', True)

        # Initialise paths
        arg['file'] = FsPath(arg['file']).resolve()
        file = arg['file']
        self._file = file
        self._lock = FsPath(file.parent, file.name + '.lock').resolve()
        self._temp = FsPath(_tempdir.name, file.name + ranID()).resolve()

        # We throw potential FileNotFoundError and FileExistsError before
        # creating the temporary file
        self._exists = True if self.file.is_file() else False
        if not self._exists and self.file.exists():
            raise NotImplementedError("ProtectFile does not yet support "
                                    + "directories or symlinks.")
        mode = arg.get('mode','r')
        self._readonly = False
        if 'r' in mode:
            if not self._exists:
                raise FileNotFoundError
            if not '+' in mode:
                self._readonly = True
        elif 'x' in mode:
            if self._exists:
                raise FileExistsError
        if self._readonly:
            self._use_temporary = False

        # Provide an expected running time (to free a file in case of crash)
        max_lock_time = arg.pop('max_lock_time', None)
        if max_lock_time is not None and self._readonly == False:
            print("Warning: Using `max_lock_time` for non read-only "
                + "files is dangerous! If the time is estimated wrongly "
                + "and a file is freed while the original process is "
                + "still running, file corruption might occur. Are you "
                + "sure this is what you want?")

        # Time to wait between trials to generate lockfile
        wait = arg.pop('wait', 1)

        # Try to make lockfile, wait if unsuccesful
        self._access = False
        while True:
            try:
                self._create_lock(max_lock_time=max_lock_time)
                # Success! Or is it....?
                # We are in the lockfile, but there is still one potential concurrency,
                # namely another process could have started creating the file while we
                # did not see it having been created yet...
                self._flush_lock()
                if not self._lock_is_ours():
                    self._wait(wait)
                    continue
                self._print_debug("init", f"created {self.lockfile}")
                break

            except FileExistsError:
                # Lockfile exists, wait and try again
                self._wait(wait)
                if max_lock_time is not None:
                    try:
                        kill_lock = False
                        with self.lockfile.open('r') as fid:
                            try:
                                info = json.load(fid)
                            except:
                                continue
                        if self._testing:
                            # This is only for tests, to be able to kill the process
                            time.sleep(1)
                        if 'free_after' in info and info['free_after'] > 0 \
                        and info['free_after'] < time.time():
                            # We free the original process by deleting the lockfile
                            # and then we go to the next step in the while loop.
                            # Note that this does not necessarily imply this process
                            # gets to use the file; which is the intended behaviour
                            # (first one wins).
                            kill_lock = True
                        if kill_lock:
                            self.lockfile.unlink()
                            self._print_debug("init",f"freed {self.lockfile} because "
                                                + "of exceeding max_lock_time")
                    except FileNotFoundError:
                        # All is fine, the lockfile disappeared in the meanwhile.
                        # Return to the while loop.
                        pass

            except PermissionError:
                # Special case: we can still access eos files when permission has expired, using `eos`
                if isinstance(self.file, EosPath):
                    try:
                        # If it already exists, we have to wait anyway for it to be freed
                        if self.lockfile.is_file():
                            self._wait(wait)
                            continue
                        # Make a local lockfile that has the sysinfo
                        local_lockfile = FsPath(_tempdir.name, file.name + '.lock').resolve()
                        if local_lockfile.exists():
                            local_lockfile.unlink()
                        self._create_lock(local_lockfile, max_lock_time, local=True)
                        self._print_debug("init", f"created local {local_lockfile}")
                        self._flush_lock(local_lockfile)
                        if not self._lock_is_ours(local_lockfile):
                            self._wait(wait)
                            continue
                        self._print_debug("init", f"created {self.lockfile} via eos cp")
                        break
                    except PermissionError:
                        # This means the `eos` command has failed as well: we really don't have access
                        raise PermissionError(f"Cannot access {self.lockfile}; permission denied.")
                else:
                    raise PermissionError(f"Cannot access {self.lockfile}; permission denied.")

        # Success!
        self._access = True
        self._delete_lock_at_finish = True

        # Store stats (to check if file got corrupted later)
        if self._check_hash and self._exists:
            self._size = self.file.size()
            self._hash = get_hash(self.file)

        # Force an update from the file system
        self._file.flush()

        # Choose file pointer:
        # To the temporary file if writing, or existing file if read-only
        if self._use_temporary:
            if self._exists:
                self._print_debug("init", f"cp {self.file=} to {self.tempfile=}")
                self.file.copy_to(self.tempfile)
            arg['file'] = self.tempfile
        self._fd = io.open(**arg)

        # Store object in class dict for cleanup in case of sysexit
        protected_open[self.file] = self


    def _wait(self, wait):
        # Add some white noise to the wait time to avoid different processes syncing
        this_wait = random.uniform(wait*0.6, wait*1.4)
        self._print_debug("init", f"waiting {this_wait}s to create {self.lockfile}")
        time.sleep(this_wait)


    def _create_lock(self, lockfile=None, max_lock_time=None):
        self.lockfile.getfid() # Look up the file on the server
        if lockfile is None:
            lockfile = self.lockfile
        free_after = -1
        if max_lock_time is not None:
            free_after = int(time.time() + max_lock_time)
        # We ensure that the variables in the lockfile always have a fixed number of characters
        ran = random.randint(0, 2**63 - 1) + os.getpid() + int(time.time_ns() % 1e9)
        self._ran = f"{ran:0>20d}"
        self._machine = f"{os.uname().nodename: >35s}"[:35]
        with lockfile.open('x') as flock:
            json.dump({
                'ran':     self._ran,
                'machine': self._machine,
                'free_after': free_after
            }, flock)


    def _flush_lock(self, local_lockfile=None):
        if local_lockfile:
            # Move it to the server lockfile
            local_lockfile.move_to(self.lockfile)  # can use specialised server commands
            assert not local_lockfile.is_file()    # sanity check
        # Flush the file on the server
        self.lockfile.flush()
        time.sleep(random.uniform(0.1, 0.2))
        if local_lockfile:
            # Move it to the server lockfile
            self.lockfile.copy_to(local_lockfile)  # can use specialised server commands
            assert local_lockfile.is_file()    # sanity check


    def _lock_is_empty(self, i=1):
        if i > 15:
            return True
        if self.lockfile.size() > 0:
            return False
        else:
            self._wait(0.2)
            return self._lock_is_empty(i+1)


    def _lock_is_ours(self, lockfile=None):
        if lockfile is None:
            lockfile = self.lockfile
        if not lockfile.exists():
            return False
        if self._lock_is_empty():
            self._print_debug("lock_is_ours", f"lockfile {lockfile} is empty")
            lockfile.unlink()
            return False
        try:
            with lockfile.open('r') as fid:
                info = json.load(fid)
        except:
            # If we cannot load the json, it might be empty or being written to
            self._print_debug("lock_is_ours", f"cannot load json info from {lockfile}")
            return False
        if 'ran' not in info or info['ran'] != self._ran:
            ran = info['ran'] if 'ran' in info else 'None'
            self._print_debug("lock_is_ours", f"ran info changed in {lockfile} ({ran} vs {self._ran})")
            return False
        if 'machine' not in info or info['machine'] != self._machine:
            machine = info['machine'] if 'machine' in info else 'None'
            self._print_debug("lock_is_ours", f"machine info changed in {lockfile} ({machine} vs {self._machine})")
            return False
        # We got here, so the lockfile is ours
        return True


    def __del__(self, *args, **kwargs):
        self.release()

    def __enter__(self, *args, **kwargs):
        return self._fd

    def __exit__(self, *args, **kwargs):
        if not self._access:
            return
        # Close file pointer
        if not self._fd.closed:
            self._fd.close()
        # Check that the lock is still ours
        if not self._lock_is_ours(self.lockfile):
            self._delete_lock_at_finish = False
            self.stop_with_error(f"Lockfile {self.lockfile} is not ours anymore.")
            return
        # Check that we did not run out of time
        try:
            with self.lockfile.open('r') as fid:
                info = json.load(fid)
        except:
            self._delete_lock_at_finish = False
            self.stop_with_error("Loading JSON from lockfile failed.")
            return
        if 'free_after' in info and info['free_after'] > 0 and info['free_after'] < time.time():
            # Max runtime was expired. We have to forfeit the job as this is a potential failure point.
            self.stop_with_error(f"Error: Job {self._file} took longer than expected ("
                + f"{round(time.time() - info['free_after'])}s. Increase max_lock_time.")
            return
        # Check that original file was not modified in between (i.e. corrupted)
        file_changed = False
        if self._use_temporary and self._check_hash and self._exists:
            new_size = self.file.size()
            new_hash = get_hash(self.file)
            if self._hash != new_hash:
                file_changed = True
            # for key, val in self._fstat.items():
            #     if key not in new_stats or val != new_stats[key]:
            #         file_changed = True
        if file_changed:
            self.stop_with_error(f"Error: File {self.file} changed during lock! "
                + f"Original size: {self._size}, new size: {new_size}. "
                + f"Original hash: {self._hash}, new hash: {new_hash}.")
        else:
            # All is fine: move result from temporary file to original
            self.mv_temp()
            # Flag the changes to the server
            self.file.getfid()
            time.sleep(random.uniform(0.1, 0.2))
            self.release()


    @property
    def file(self):
        return self._file

    @property
    def lockfile(self):
        return self._lock

    @property
    def tempfile(self):
        return self._temp


    def mv_temp(self, destination=None):
        """Move temporary file to 'destination' (the original file if destination=None)"""
        if not self._access:
            return
        if self._use_temporary:
            if destination is None:
                # Move temporary file to original file
                self._print_debug("mv_temp", f"cp {self.tempfile=} to {self.file=}")
                self.tempfile.copy_to(self.file)
                # # Check if copy succeeded
                # if self._check_hash and get_hash(self.tempfile) != get_hash(self.file):
                #     self.stop_with_error(f"Warning: tried to copy temporary file {self.tempfile} into {self.file}, "
                #           + "but hashes do not match!")
            else:
                self._print_debug("mv_temp", f"cp {self.tempfile=} to {destination=}")
                self.tempfile.copy_to(destination)
            self._print_debug("mv_temp", f"unlink {self.tempfile=}")
            self.tempfile.unlink()


    def stop_with_error(self, message):
        """Fail the job, and potentially save calculation results"""
        if not self._access:
            return
        self._access = False
        results_saved = False
        alt_file = None
        if self._use_temporary:
            extension = f"__{datetime.datetime.now().isoformat()}.result"
            alt_file = FsPath(self.file.parent, self.file.name + extension).resolve()
            self.mv_temp(alt_file)
            results_saved = True
        raise ProtectFileError(message, results_saved, alt_file)


    def release(self, pop=True):
        """Clean up lockfile and tempfile"""
        # Overly verbose in checking, as to make sure this never fails
        # (to avoid being stuck with remnant lockfiles)
        # Close main file pointer
        if hasattr(self,'_fd') and hasattr(self._fd,'closed') and not self._fd.closed:
            self._fd.close()
        # Delete temporary file
        if hasattr(self,'_temp') and hasattr(self._temp,'is_file') and self._temp.is_file():
            self._print_debug("release", f"unlink {self.tempfile}")
            self.tempfile.unlink()
        # Delete lockfile
        if hasattr(self, '_delete_lock_at_finish') and self._delete_lock_at_finish:
            if hasattr(self,'_lock') and hasattr(self._lock,'is_file') and self._lock.is_file():
                self._print_debug("release", f"unlink {self.lockfile}")
                self.lockfile.unlink()
        # Remove file from the protected register
        if pop:
            protected_open.pop(self._file, 0)


    def _print_debug(self, prc, msg):
        if self._debug:
            print(f"({self._file.name}) {prc}: {msg}\n")


class ProtectFileError(Exception):
    def __init__(self, message, results_saved, alt_file):
        mess = f"ProtectFile failed! {message}"
        if results_saved:
            mess += f" Saved calculation results in {alt_file.name}."
        super().__init__(mess)
        self.message = message
        self.results_saved = results_saved
        self.alt_file = alt_file

    def __reduce__(self):
        return (ProtectFileError, (self.message, self.results_saved, self.alt_file))
