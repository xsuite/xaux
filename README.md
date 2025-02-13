# Xaux

Xaux is a package with support tools, both for general usage and tune for CERN / Xsuite usage. It is thoroughly tested for all python versions from 3.8 onwards, to ensure stability. The following tools are provided:


### Singleton
The decorator `@singleton` will redefine a class into a singleton such that only one instance exists and the same instance is returned every time the class is instantiated.

- This is implemented by letting the class inherit from itself and renaming it, as this was the cleanest way to ensure inheritance compatibility. Each child of a singleton class will be its own singleton.
- Each re-initialisation of the singleton will keep the class attributes, and for this reason, the `__init__` method should not have any required arguments. This is asserted at the class creation time.
- By default, the singleton allows setting private attributes in the constructor, but this can be overridden by setting `allow_underscore_vars_in_init=False`.
- The singleton can be reset by calling the `delete()` method of the class, which will invalidate any existing instances.
- The decorator provides a `get_self()` method, which is a class method that is more relaxed than the constructor, as it allows passing any `**kwargs` even if they aren't attributes for the singleton (these  will then just be ignored). This is useful for kwargs filtering in getters or specific functions.

Example usage:

```python
@singleton
class MyClass:

    def __init__(self, value=10):
        self.value = value
```
```python
>>> instance1 = MyClass(value=8)
>>> instance2 = MyClass(value=9)
>>> print(instance1.value)
9
>>> print(instance2.value)
9
>>> print(instance1 is instance2)
True
>>> instance3 = MyClass()
>>> print(instance1.value)
9
```


### Class Property
The descriptor `@ClassProperty` works similar as `@property` but is used to define class properties (instead of instance properties).

- Contrary to a regular `property`, a `__set__` or `__delete__` call on the owner class would not be intercepted because of how Python classes work. For this reason, it is necessary to use a dedicated metaclass, the `ClassPropertyMeta`, to intercept these calls, even when no setter or deleter is defined (as otherwise the attribute would not be read-only and could still be overwritten).
- The descriptor class keeps a registry of all `ClassProperty` attributes for each class, which is accessible with the `get_properties()` method.
- Whenever a class has a `ClassProperty`, a `ClassPropertyAccessor` named `classproperty` will be attached to it, providing an attribute-like interface to the `ClassProperty` attributes of a class for introspection. Use it as `?MyClass.classproperty.my_class_property` to get the introspect in `IPython`.
- An important caveat is that regular class attributes do not always behave as expected when inherited, which might be an issue when a `ClassProperty` uses such a regular class attribute (for instance as the private attribute it is encapsulating). Indeed, when the parent has a class attribute `_prop` it will not be copied unto the child, and any `ClassProperty.setter` applied on the child will inevitably update the parent's attribute as well. To handle this, one can define a dict `_classproperty_dependencies` in the class to declare all dependent regular class attributes and their initial values. The `ClassPropertyMeta` then copies these attributes to the child.

Example usage:

```python
class MyClass(metaclass=ClassPropertyMeta):
    _classproperty_dependencies = {
        '_my_classproperty': 0
    }

    @ClassProperty
    def my_class_property(cls):
        print("In getter")
        return cls._my_classproperty

    @my_class_property.setter
    def my_class_property(cls, value):
        print("In setter")
        cls._my_classproperty = value

    @my_class_property.deleter
    def my_class_property(cls):
        print("In deleter")
        cls._my_classproperty = 0
```
```python
>>> print(MyClass.my_class_property)
In getter
0
>>> MyClass.my_class_property = 3
In setter
>>> print(MyClass.my_class_property)
In getter
3
>>> del MyClass.my_class_property
In deleter
>>> print(MyClass.my_class_property)
In getter
0
```


### FsPath
This is an extension to the `Path` class from `pathlib`, which is adapted to work, besides on regular local file systems, robustly and efficiently on AFS (the Andrew File System) and EOS (a storage-oriented file system developed at CERN). It defines three classes, `LocalPath`, `AfsPath`, and `EosPath`, and a class factory `FsPath`. The correct class will be automatically instantiated based on the file system on which the path sits. Care is taken to correctly resolve a path when symlinks are present.

The main advantage is that for a whole set of file operations, the standard `Path` implementations are overwritten by specific server commands native to `AFS` and `EOS`. This ensures that paths are always in sync with their server nodes. Furthermore, new methods are added to `FsPath` which are missing from `Path`. These are `getfid()`, `flush()`, `lexists()`, `is_broken_symlink()`, `rmtree()`, `copy_to()`, `move_to()`, and `size()`.

Note that `LocalPath` is just a regular `Path` but with additional access to the `FsPath` methods.

Example usage:

```python
>>> path = FsPath('/newhome/fvanderv/work')  # 'work' is a symbolic link on a local file system that points to an AFS folder
>>> path
LocalPosixPath('/newhome/fvanderv/work')
>>> path.resolve()
AfsPosixPath('/afs/cern.ch/work/f/fvanderv')
```
```python
>>> path = FsPath('/eos/project/c/collimation-team')
>>> path
EosPosixPath('/eos/project/c/collimation-team')
>>> path.eos_path # EosPath objects have a few specific attributes that correctly resolve EOS components
/eos/project/c/collimation-team
>>> path.eos_path_full
root://eosproject.cern.ch//eos/project/c/collimation-team
>>> path.eos_instance
project
```


### ProtectFile
This is a wrapper around a file pointer, protecting it with a lockfile. It is meant to be used inside a context, where the entering and leaving of a context ensures file protection. The moment the object is instantiated, a lockfile is generated (which is destroyed after leaving the context). Attempts to access the file will be postponed as long as a lockfile exists. Furthermore, while in the context, file operations are done on a temporary file, that is only moved back when leaving the context.

The reason to lock read access as well is that we might work with immutable files. The following scenario might happen: a file is read by process 1, some calculations are done by process 1, the file is read by process 2, and the result of the calculations is written by process 1. Now process 2 is working on an outdated version of the file. Hence the full process should be locked in one go: reading, manipulating/calculating, and writing.

Several systems are in place to (almost) completely rule out concurrency and race conditions, to avoid file corruption. In the rare case where file corruption occurs, the original file is restored and the updated file stored under a different name.

The tool works particularly well on EOS using the FsPath mechanics, however, on AFS it cannot be used reliably as different node servers can be out-of-sync with each other for a few seconds up to minutes.

Example usage:

```python
import json
from xaux import ProtectFile
with ProtectFile(info.json, 'r+', wait=1) as pf:
    meta = json.load(pf)
    meta.update({'author': 'Emperor Claudius'})
    pf.truncate(0)          # Delete file contents (to avoid appending)
    pf.seek(0)              # Move file pointer to start of file
    json.dump(meta, pf, indent=2, sort_keys=False))
```

### General Tools
These are a set of lightweight tools:
 - `timestamp` provides an easy way to get timestamps into logs and filenames (with second, millisecond, or microsecond accuracy).
 - `ranID` generates a Base64 encoded random ID string, useful for in filenames or element names.
 - `system_lock` is typically used for a cronjob. It will exit the python process if the previous cronjob did not yet finish (based on a custom lockfile name).
 - `get_hash` is a quick way to hash a file, in chunks of a given size.

Then there are also a few tools to get info about a function's arguments, which are only accessible via `xaux.tools` and are essentially just wrappers around functions in `inspect`. These are `count_arguments`, `count_required_arguments`, `count_optional_arguments`, `has_variable_length_arguments`, `has_variable_length_positional_arguments`, and `has_variable_length_keyword_arguments`.


### Dev Tools for Xsuite
These are tools used for the maintenance and deployment of python packages. They are not in the test suite, and only accessible via `xaux.dev_tools`. The low-level functionality is a set of wrappers around `gh` (GitHub CLI), `git`, and `poetry`, while the higher-level functions are `make_release`, `make_release_branch`, `rename_release_branch` which are tailored to Xsuite and go through the same sequence of steps (verifying the release version number, making a PR to main, accepting it, publishing to PyPi, and making draft release notes on GitHub), while asserting the local workspace is clean and asking confirmation at each step. These are currently used as the default tools to maintain and deploy `xaux`, `xboinc`, `xcoll`, and `xdyna`.

Finally, there are also some tools that wrap around `pip` and the `PyPi` API to get available package versions and make temporary installations of a specific package version from within python.
