import yaml
from .dict_print import dict_print


def _type_conv(val):
    """Convert None to 'null'"""
    return "null" if val is None else val


def _write_dict(data, file, tab="    ", _first=True):
    """Given an open file, write the args to it in dictionary format

    Parameters
    ----------
    data : dict
        The data dictionary to be read from
    file : file
        The open file to be written to
    tab : str
        Formatting for indenting args
    _first : bool
        Internal use for recursion tracking
    """

    if _first:
        tab = ""
    for key in data.keys():
        if isinstance(data[key], dict):
            # Use recursion if a dict is encountered
            file.write(f"{tab}{key}:\n")
            _write_dict(data[key], file, tab=tab + "    ", _first=False)
        elif isinstance(data[key], list):
            # Convert list to new lines
            file.write(f"{tab}{key}:\n")
            for d in data[key]:
                file.write(f"{tab}  - {_type_conv(d)}\n")
        else:
            # Write normally
            file.write(f"{tab}{key}: {_type_conv(data[key])}\n")


def _get_dict_exclude(obj, exclude=["subset"]):
    """Return a dictionary of attributes from the parser with optional exclusions

    Parameters
    ----------
    obj : args_from_YAML
        The parser to be read from
    exclude : list
        The names of attributes to exclude
    """

    temp = {}
    for k, v in obj.__dict__.items():
        if not k in exclude:
            if not isinstance(v, args_from_YAML):
                temp[k] = v
            else:
                # Use recursion if needed
                temp[k] = _get_dict_exclude(v, exclude=exclude)
    return temp


def compare_args(argsA, argsB, _top_level=True, _post=""):
    dA = argsA.get_kwargs()
    dB = argsB.get_kwargs()

    keyA = set(dA.keys())
    keyB = set(dB.keys())

    uniques = keyA.union(keyB)
    b_missing = keyA - keyB
    b_only = keyB - keyA

    B_only = {k: argsB[k] for k in b_only}
    B_missing = {k: argsA[k] for k in b_missing}

    both_have_diff = {}
    for u in uniques:
        try:
            if argsA[u] != argsB[u]:
                if isinstance(argsA[u], args_from_YAML):
                    tmp = compare_args(argsA[u], argsB[u], False, _post + "." + u)
                    both_have_diff.update(tmp)
                else:
                    both_have_diff[u + _post] = f"{argsA[u]} | {argsB[u]}"
        except AttributeError:
            continue

    if not _top_level:
        return both_have_diff

    any_diff = False
    if len(B_missing) > 0:
        print("===== Missing from B =====")
        dict_print(B_missing)
        any_diff = True

    if len(B_only) > 0:
        print("===== Only in B =====")
        dict_print(B_only)
        any_diff = True

    if len(both_have_diff) > 0:
        print("===== Different <A | B> =====")
        dict_print(both_have_diff)
        any_diff = True

    if not any_diff:
        print("No differences found.")


def compare_yaml(fileA, fileB):
    compare_args(args_from_YAML(fileA), args_from_YAML(fileB))


class args_from_YAML:
    """Parse a given YAML file and generate a class with those attributes"""

    def __init__(
        self,
        config_path,
        subset=None,
        verbose=False,
        _local_subsets=False,
        _info=None,
    ):
        """
        Parameters
        ----------
        config_path : str
            The path the .yaml file
        subset : str | None
            If only a subset of the file is needed, then specify
            the attribute name representing that subset
        verbose : bool
            Whether additional info will be printed
        """
        if _info is None:
            # _top-level
            self.config_path = config_path
        else:
            self.subset = subset
        self.reset(
            subset=subset, _info=_info, verbose=verbose, _local_subsets=_local_subsets
        )

    def save_to_yaml(self, path, mode="w", exclude=["subset"]):
        """Write the current state of the class instance to a yaml file"""
        with open(path, mode) as file:
            _write_dict(_get_dict_exclude(self, exclude), file)

    def reset(self, subset="main", verbose=False, _info=None, _local_subsets=False):
        """Recreate class instance with the provided kwargs"""
        path = None
        if hasattr(self, "config_path"):
            path = self.config_path
        _configure(
            self,
            path,
            _info=_info,
            subset=subset,
            verbose=verbose,
            _local_subsets=_local_subsets,
        )

    def update_reuse(self, st_str="${", en_str="}", verbose=True):
        """
        Subsets may have copies of higher-level parameters
        By default, any config items with the format "${name}" will be filled using a higher-level instance of "name"
        For example; if "seed: 0" and "subconfig.seed: ${seed}" exist, then it becomes "subconfig.seed: 0" after
        running <self.update_reuse()>
        """
        _process_reuse(self, self, st_str=st_str, en_str=en_str, verbose=verbose)

    def pop(self, key, default=None):
        """Try to return the attribute and remove it from the parser"""
        return self.__dict__.pop(key, default)

    def __iter__(self):
        """Return the _top-level attribute names via 'for key in class_inst'"""
        for key in self.__dict__.keys():
            yield key

    def __setitem__(self, key, value):
        """Support setting values via 'class_inst["key"] = value'"""
        setattr(self, key, value)

    def __getitem__(self, key):
        """Support getting values via 'class_inst["key"]'"""
        return getattr(self, key)

    def get(self, key):
        """Given an attribute name, or a list of nested attribute names return a single attribute value

        Example: use key ["A", "B", "C", "D"] to retrieve attribute A.B.C.D
        """
        return get_nested_attribute(self, key)  # self.__dict__.get(key, default)

    def set(self, key, value):
        """Given an attribute name or a list of nested attribute names, and a value, set the attribute to that value

        Example: use key ["A", "B", "C", "D"] to set attribute A.B.C.D
        """
        _nested_set(self, key, value)

    def get_kwargs(self):
        """Return the attributes and values of the parser as a dictionary"""
        return _get_dict_exclude(self)

    def print(self):
        """For pretty printing of the parser's attributes and values"""
        dict_print(_get_dict_exclude(self))
        print()

    def __str__(self) -> str:
        return f"{_get_dict_exclude(self)}"


def _try_float(obj):
    """Try to convert attribute values to float or int in-place"""
    for k, v in obj.__dict__.items():
        # If the value is not already converted to a number
        if isinstance(v, str):
            try:
                tmp = float(v)
                if int(tmp) - tmp == 0:
                    # If equivalent to integer then, assume int
                    tmp = int(tmp)
                obj[k] = tmp
            except ValueError:
                # Can't convert to float, so ignore it
                continue
        elif isinstance(v, args_from_YAML):
            # Recursion
            _try_float(v)


def _configure(
    obj,
    path=None,
    subset=None,
    verbose=False,
    _info=None,
    _local_subsets=False,
    _top=False,
):
    """Performs the YAML file parsing recursively

    Parameters
    ----------
    obj : args_from_YAML
        The parent parser
    path : str | None
        The YAML file path
    subset : str | None
        Retrieve only a subset of the config, specified
        by attribute name
    verbose : bool
        Whether additional info is printed
    """
    if _info is None:
        _top = True
        with open(path, "r") as f:
            _info = yaml.safe_load(f)

    for k, v in _info.items():
        if k == "_local_":
            _local_subsets = v
        if isinstance(v, dict):
            if (k == subset and _top) or not _top or subset is None:
                if _local_subsets:
                    # Add all values to the _top-level class
                    _configure(
                        obj,
                        path=path,
                        _info=v,
                        subset=None,
                        _local_subsets=_local_subsets,
                    )
                else:
                    # Recursively add subclasses to contain the dictionary values as needed (per the given YAML structure)
                    # Ex: A.B.C.D.value
                    setattr(obj, k, args_from_YAML(path, _info=v, subset=k))
        else:
            setattr(obj, k, v)

    _try_float(obj)
    if verbose:
        print(f"AutoConfig using: {path}, subset: {subset}")
        # obj.print()


def reassign(target, source):
    """All attributes from 'target' class instance are added to 'source' class instance"""
    for k, v in source.__dict__.items():
        setattr(target, k, v)


def get_nested_attribute(obj, att_list):
    """Retrieve attribute value from object

    Parameters
    ----------
    obj : args_from_YAML
        An object with attributes
    att_list : str | list [str, str, ...]
        If a string, then retrieve that attribute value
        If a list of strings, then follow the nested attribute names to retrieve the value
    """
    if isinstance(att_list, list) or isinstance(att_list, tuple):
        out = getattr(obj, att_list[0])
        for i in range(1, len(att_list)):
            out = getattr(out, att_list[i])
    else:
        out = getattr(obj, att_list)
    return out


def _nested_set(obj, att_list, value):
    """Set attribute value of object

    Parameters
    ----------
    obj : args_from_YAML
        An object with attributes
    att_list : str | list [str, str, ...]
        If a string, then set that attribute value
        If a list of strings, then follow the nested attribute names to set the value
    value : any
        The value to be set for the specified attribute
    """
    if isinstance(att_list, list) or isinstance(att_list, tuple):
        att = att_list[0]
        if isinstance(obj[att], args_from_YAML):
            _nested_set(obj[att], att_list[1:], value)
        else:
            setattr(obj, att, value)
    else:
        setattr(obj, att_list, value)


def _process_reuse(
    data,
    original_data,
    st_str="${",
    en_str="}",
    ignore="???",
    max_depth=10,
    verbose=True,
):
    """
    Subsets may have copies of higher-level parameters
    By default, any config items with the format "${name}" will be filled using a higher-level instance of "name"
    For example; if "seed: 0" and "subconfig.seed: ${seed}" exist, then it becomes "subconfig.seed: 0" after
    running <self.update_reuse()>

    Parameters
    ----------
    data : args_from_YAML
        The parser to be updated
    original_data : args_from_YAML
        Typically, the same parser as "data", but can be a different one
    st_str : str
        The beginning characters of the reuse identifier
    en_str : str
        The end characters of the reuse identifier
    ignore : str
        If only a partial update is desired, then set the high-level attribute's value to this and
        it will be ignored
    max_depth : int
        Maximum recursion depth
    verbose : bool
        Whether additional info will be printed
    """

    def _check_replace(v):
        # Check if this value matches the replacement format and if so, remove the identifiers to get the real string
        if (
            isinstance(v, str)
            and v[: len(st_str)] == st_str
            and v[-len(en_str) :] == en_str
        ):
            return [s.replace(st_str, "").replace(en_str, "") for s in v.split(".")]
        else:
            return None

    for k, v in data.__dict__.items():
        temp = _check_replace(v)
        if temp is not None:
            try:
                # Account for nested ${} inside references. Use a for loop to prevent high recursions
                for _ in range(max_depth):
                    n_att = get_nested_attribute(original_data, temp)
                    temp = _check_replace(n_att)
                    if temp is None:
                        break
                # If an ignore value is specified, then do not perform updates with that value
                # The ignored source value(s) can be updated later and this function re-run
                if ignore is None or n_att != ignore:
                    setattr(data, k, n_att)
            except AttributeError:
                if verbose:
                    print(
                        f'WARNING: AutoConfig could not find the following term for reuse: "{".".join(temp)}". Suppress warning with "verbose=False"'
                    )
        elif isinstance(v, args_from_YAML):
            _process_reuse(v, original_data, verbose=verbose)
