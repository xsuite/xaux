"""
This package is an attempt to make file reading/writing (possibly concurrent) more reliable.

Last update 23/02/2024 - F.F. Van der Veken
"""

import atexit
import datetime
import hashlib
import io
from pathlib import Path
import random
import shutil
import tempfile
import time
import json
import subprocess

tempdir = tempfile.TemporaryDirectory()
protected_open = {}

# TODO: make more robust
# Use debug flag below to inspect steps in file IO
_debug = False

def _print_debug(prc, msg):
    if _debug:
        print(prc,": ", msg, "\n")

def exit_handler():
    """This handles cleaning of potential leftover lockfiles and backups."""
    for file in protected_open.values():
        file.release(pop=False)
    tempdir.cleanup()
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

def get_fstat(filename):
    stats = Path(filename).stat()
    return {
                'n_sequence_fields': stats.n_sequence_fields,
                'n_unnamed_fields':  stats.n_unnamed_fields,
                'st_mode':           stats.st_mode,
                'st_ino':            stats.st_ino,
                'st_dev':            stats.st_dev,
                'st_uid':            stats.st_uid,
                'st_gid':            stats.st_gid,
                'st_size':           stats.st_size,
                'st_mtime_ns':       stats.st_mtime_ns,
                'st_ctime_ns':       stats.st_ctime_ns,
            }

def xrdcp_installed():
    try:
        cmd = subprocess.run(["xrdcp", "--version"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, check=True)
        return cmd.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False




class ProtectFile:
    """A wrapper around a file pointer, protecting it with a lockfile and backups.

    Use
    ---
    It is meant to be used inside a context, where the entering and leaving of a
    context ensures the file protection. The moment the object is instantiated, a
    lockfile is generated (which is destroyed after leaving the context). Attempts
    to access the file will be postponed as long as a lockfile exists. Furthermore,
    while in the context, file operations are done on a temporary file, that is
    only moved back when leaving the context.

    The reason to lock read access as well, is that we might work with immutable
    files. The following scenario might happen: a file is read by process 1, some
    calculations are done by process 1, the file is read by process 2, and the
    result of the calculations are written by process 1. Now process 2 is working
    on an outdated version of the file. Hence the full process should be locked in
    one go: reading, manipulating/calculating, writing.

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
    backupfile : pathlib.Path
        The path to a backup file in the same folder. This is to not lose the file
        in case of a catastrophic crash. This can be switched off by setting
        'backup_during_lock'=False. On the other hand, the option 'backup'=True
        will keep the backup file even after destroying the ProtectFile object. Not
        used when a ProtectFile object is instantiated in read-only mode ('r' or
        'rb'), unless 'backup_if_readonly'=True.

    Examples
    --------
    Reading in a file (while making sure it is not written to by another process):

    >>> from protectfile import ProtectFile
    >>> with ProtectFile('thebook.txt', 'r', backup=False, wait=1) as pf:
    >>>    text = pf.read()

    Reading and appending to a file:

    >>> from protectfile import ProtectFile
    >>> with ProtectFile('thebook.txt', 'r+', backup=False, wait=1) as pf:
    >>>    text = pf.read()
    >>>    pf.write("This string will be added at the end of the file, \
    ...               however, it won't be added to the 'text' variable")

    Reading and updating a JSON file:

    >>> import json
    >>> from protectfile import ProtectFile
    >>> with ProtectFile(info.json, 'r+', backup=False, wait=1) as pf:
    >>>     meta = json.load(pf)
    >>>     meta.update({'author': 'Emperor Claudius'})
    >>>     pf.truncate(0)          # Delete file contents (to avoid appending)
    >>>     pf.seek(0)              # Move file pointer to start of file
    >>>     json.dump(meta, pf, indent=2, sort_keys=False))

    Reading and updating a Parquet file:

    >>> import pandas as pd
    >>> from protectfile import ProtectFile
    >>> with ProtectFile(mydata.parquet, 'r+b', backup=False, wait=1) as pf:
    >>>     data = pd.read_parquet(pf)
    >>>     data['x'] += 5
    >>>     pf.truncate(0)          # Delete file contents (to avoid appending)
    >>>     pf.seek(0)              # Move file pointer to start of file
    >>>     data.to_parquet(pf, index=True)
    
    Reading and updating a json file in EOS with xrdcp:

    >>> from protectfile import ProtectFile
    >>> eos_url = 'root://eosuser.cern.ch/'
    >>> fname = '/eos/user/k/kparasch/test.json'
    >>> with ProtectFile(fname, 'r+', eos_url=eos_url) as pf:
    >>>     pass
    """

    def __init__(self, *args, **kwargs):
        """A ProtectFile object, to be used only in a context.

        Parameters
        ---------
        wait : float, default 1
            When a file is locked, the time to wait in seconds before trying to
            access it again.
        backup_during_lock : bool, default False
            Whether or not to use a temporary backup file, to restore in case of
            failure.
        backup : bool, default False
            Whether or not to keep this backup file after the ProtectFile object
            is destroyed.
        backup_if_readonly : bool, default False
            Whether or not to use the backup mechanism when a file is in read-only
            mode ('r' or 'rb').
        check_hash : bool, default True
            Whether or not to verify by hash that the move of the temporary file to
            the original file succeeded.
        max_lock_time : float, default None
            If provided, it will write the maximum runtime in seconds inside the
            lockfile. This is to avoided crashed accesses locking the file forever.
        eos_url : string, default None
            If provided, it will use xrdcp to copy the temporary file to eos and back.

        Additionally, the following parameters are inherited from open():
            'file', 'mode', 'buffering', 'encoding', 'errors', 'newline', 'closefd', 'opener'
        """

        argnames_open = ['file', 'mode', 'buffering', 'encoding', 'errors', 'newline', 'closefd', 'opener']
        arg = dict(zip(argnames_open, args))
        arg.update(kwargs)

        wait = arg.pop('wait', 1)
        # add some white noise to the wait time to avoid different processes syncing
        wait += abs(random.normalvariate(0, 1e-1*wait))
        # Backup during locking process (set to False for very big files)
        self._do_backup = arg.pop('backup_during_lock', False)
        # Keep backup even after unlocking
        self._keep_backup = arg.pop('backup', False)
        # If backup is to be kept, then it should be activated anyhow
        if self._keep_backup:
            self._do_backup = True
        self._backup_if_readonly = arg.pop('backup_if_readonly', False)
        self._check_hash = arg.pop('check_hash', True)

        self._eos_url = arg.pop('eos_url', None)
        if self._eos_url is not None:
            self.original_eos_path = arg['file']
            if not self._eos_url.startswith("root://eos") or not self._eos_url.endswith('.cern.ch/'):
                raise NotImplementedError(f'Invalid EOS url provided: {self._eos_url}')
            if not str(self.original_eos_path).startswith("/eos"):
                raise NotImplementedError(f'Only /eos paths are supported with eos_url.')
            if not xrdcp_installed():
                raise RuntimeError("xrdcp is not installed.")
            self.original_eos_path = self._eos_url + self.original_eos_path

        # Initialise paths
        arg['file'] = Path(arg['file']).resolve()
        file = arg['file']
        self._file = file
        self._lock = Path(file.parent, file.name + '.lock').resolve()
        self._temp = Path(tempdir.name, file.name).resolve()

         
        # We throw potential FileNotFoundError and FileExistsError before
        # creating the backup and temporary files
        self._exists = True if self.file.is_file() else False
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

        
        # Provide an expected running time (to free a file in case of crash)
        max_lock_time = arg.pop('max_lock_time', None)
        if max_lock_time is not None and self._readonly == False \
        and self._file.suffix != '.lock':
            print("Warning: Using `max_lock_time` for non read-only "
                + "files is dangerous! Are you sure this is what you want?")

        # Try to make lockfile, wait if unsuccesful
        while True:
            try:
                _print_debug("Init",f"open {self.lockfile}")
                self._flock = io.open(self.lockfile, 'x')
                break
            except (IOError, OSError, FileExistsError):
                _print_debug("Init", f"waiting {wait}s to create {self.lockfile}")
                time.sleep(wait)
                if max_lock_time is not None:
                    # Check if the original process that locked the file
                    # might have crashed. If yes, this process can take over.
                    # We are only allowed to do this for 10 iterations
                    iteration = 0
                    for suf in self.lockfile.suffixes:
                        if suf == '.lock':
                            iteration += 1
                        else:
                            iteration = 0
                    if iteration < 10:
                        # Try to open the lock
                        with ProtectFile(self.lockfile, 'r+', wait=0.1, \
                                         max_lock_time=10) as pf:
                            info = json.load(pf)
                            if 'free_after' in info and info['free_after'] < time.time():
                                # We free the original process
                                # Note that we have to udpate the info in the lockfile
                                # before freeing the lockfile!
                                json.dump({
                                    'free_after': time.time() + 2*max_lock_time
                                }, pf)
                                # We still have to provide the file pointer as the
                                # original pointer failed with FileExistsError
                                self._flock = io.open(self.lockfile, 'r+')
                                break
                    else:
                        raise RuntimeError("Too many lockfiles!")

        # Store lock information
        if max_lock_time is not None:
            json.dump({
                'free_after': time.time() + 1.2*max_lock_time
            }, self._flock)
            self._flock.close()

        # Make a backup if requested
        if self._readonly and not self._backup_if_readonly:
            self._do_backup = False
        if self._do_backup and self._exists:
            self._backup = Path(file.parent, file.name + '.backup').resolve()
            _print_debug("Init", f"cp {self.file=} to {self.backupfile=}")
            shutil.copy2(self.file, self.backupfile)
        else:
            self._backup = None

        # Store stats (to check if file got corrupted later)
        if self._exists:
            self._fstat = get_fstat(self.file)

        # Choose file pointer:
        # To the temporary file if writing, or existing file if read-only
        # TODO: if the original file is large, using a temporary file might be extremely
        #       slow if many processes write to it concurrently
        if not self._readonly:
            if self._exists:
                if self._eos_url is not None:
                    _print_debug("Init", f"xrdcp {self.original_eos_path} to {self.tempfile=}")
                    self.xrdcp(self.original_eos_path, self.tempfile)
                else:
                    _print_debug("Init", f"cp {self.file=} to {self.tempfile=}")
                    shutil.copy2(self.file, self.tempfile)
            arg['file'] = self.tempfile
        self._fd = io.open(**arg)

        # Store object in class dict for cleanup in case of sysexit
        protected_open[self.file] = self


    def __del__(self, *args, **kwargs):
        self.release()

    def __enter__(self, *args, **kwargs):
        return self._fd

    def __exit__(self, *args, **kwargs):
        # Close file pointer
        if not self._fd.closed:
            self._fd.close()
        # Check that original file was not modified in between (i.e. corrupted)
        # TODO: verify that checking file stats is 1) enough, and 2) not
        #       potentially problematic on certain file systems
        if self._exists and get_fstat(self.file) != self._fstat:
            print(f"Error: File {self.file} changed during lock!")
            # If corrupted, restore from backup
            # and move result of calculation (i.e. tempfile) to the parent folder
            print("Old stats:")
            print(self._fstat)
            print("New stats:")
            print(get_fstat(self.file))
            self.restore()
        else:
            # All is fine: move result from temporary file to original
            self.mv_temp()
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

    @property
    def backupfile(self):
        return self._backup

    def mv_temp(self, destination=None):
        """Move temporary file to 'destination' (the original file if destination=None)"""
        if not self._readonly:
            if destination is None:
                # Move temporary file to original file
                if self._eos_url is not None:
                    _print_debug("Mv_temp", f"xrdcp {self.tempfile=} to {self.original_eos_path=}")
                    self.xrdcp(self.tempfile, self.original_eos_path)
                else:   
                    _print_debug("Mv_temp", f"cp {self.tempfile=} to {self.file=}")
                    shutil.copy2(self.tempfile, self.file)
                # Check if copy succeeded
                if self._check_hash and get_hash(self.tempfile) != get_hash(self.file):
                    print(f"Warning: tried to copy temporary file {self.tempfile} into {self.file}, "
                          + "but hashes do not match!")
                    self.restore()
            else:
                if self._eos_url is not None:
                    _print_debug("Mv_temp", f"xrdcp {self.tempfile=} to {destination=}")
                    self.xrdcp(self.tempfile, destination)
                else:   
                    _print_debug("Mv_temp", f"cp {self.tempfile=} to {destination=}")
                    shutil.copy2(self.tempfile, destination)
            _print_debug("Mv_temp", f"unlink {self.tempfile=}")
            self.tempfile.unlink()


    def restore(self):
        """Restore the original file from backup and save calculation results"""
        if self._do_backup:
            _print_debug("Restore", f"rename {self.backupfile} into {self.file}")
            self.backupfile.rename(self.file)
            print('Restored file to previous state.')
        if not self._readonly:
            if self._eos_url is not None:
                extension = f"__{datetime.datetime.now().isoformat()}.result"
                alt_file = self.original_eos_path + extension
            else:
                alt_file = Path(self.file.parent, self.file.name + extension).resolve()
            self.mv_temp(alt_file)
            print(f"Saved calculation results in {alt_file.name}.")


    def release(self, pop=True):
        """Clean up lockfile, tempfile, and backupfile"""
        # Overly verbose in checking, as to make sure this never fails
        # (to avoid being stuck with remnant lockfiles)
        if hasattr(self,'_fd') and hasattr(self._fd,'closed') and not self._fd.closed:
            self._fd.close()
        if hasattr(self,'_temp') and hasattr(self.tempfile,'is_file') and self.tempfile.is_file():
            self.tempfile.unlink()
        if hasattr(self,'_do_backup') and hasattr(self,'_backup') and \
                hasattr(self.backupfile,'is_file') and hasattr(self,'_keep_backup') and \
                self._do_backup and self.backupfile.is_file() and not self._keep_backup:
            _print_debug("Release", f"unlink {self.backupfile}")
            self.backupfile.unlink()
        if hasattr(self,'_flock') and hasattr(self._flock,'closed') and not self._flock.closed:
            self._flock.close()
        if hasattr(self,'_lock') and hasattr(self.lockfile,'is_file') and self.lockfile.is_file():
            _print_debug("Release", f"unlink {self.lockfile}")
            self.lockfile.unlink()
        if pop:
            protected_open.pop(self._file, 0)
        
    def xrdcp(self, source=None, destination=None):
        if source is None or destination is None:
            raise RuntimeError("Source or destination not specified in xrdcp command.")
        if self._eos_url is None:
            raise RuntimeError("self._eos_url is None, while it shouldn't have been.")

        subprocess.run(["xrdcp", "-f", f"{str(source)}", f"{str(destination)}"],
                       check=True)


