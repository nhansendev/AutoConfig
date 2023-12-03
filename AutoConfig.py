import os
import yaml
from dict_print import dict_print


def argparse_to_YAML(parser, destination, filename="config.yaml"):
    if not os.path.exists(destination):
        raise FileNotFoundError(destination)

    lines = []
    choices = []
    for act in parser._actions:
        # ignore the help action
        if act.default != "==SUPPRESS==":
            lines.append(
                [
                    f'{act.dest}: {act.default if act.default is not None else "null"}',
                    f"# {act.help}\n",
                ]
            )
            if act.choices is not None:
                choices.append(
                    f"# {act.dest} choices:\n  # "
                    + "\n  # ".join([str(a) for a in act.choices])
                    + "\n"
                )
            else:
                choices.append(None)

    longest = max([len(line[0]) for line in lines])

    path = os.path.join(destination, filename)
    with open(path, "w") as file:
        for line, choice in zip(lines, choices):
            file.write(line[0] + (longest + 2 - len(line[0])) * " " + line[1])
            if choice is not None:
                file.write(choice)

    print(f"YAML file written to: {path}")


def _type_conv(val):
    return "null" if val is None else val


def _write_dict(data, file, tab="    ", _first=True):
    if _first:
        tab = ""
    for key in data.keys():
        if isinstance(data[key], dict):
            file.write(f"{tab}{key}:\n")
            _write_dict(data[key], file, tab=tab + "    ", _first=False)
        elif isinstance(data[key], list):
            file.write(f"{tab}{key}:\n")
            for d in data[key]:
                file.write(f"{tab}  - {_type_conv(d)}\n")
        else:
            file.write(f"{tab}{key}: {_type_conv(data[key])}\n")


def _get_dict_exclude(obj, exclude=["subset"]):
    temp = {}
    for k, v in obj.__dict__.items():
        if not k in exclude:
            if not isinstance(v, args_from_YAML):
                temp[k] = v
            else:
                temp[k] = _get_dict_exclude(v, exclude=exclude)
    return temp


class args_from_YAML:
    def __init__(
        self,
        config_path,
        subset=None,
        verbose=False,
        _local_subsets=False,
        _info=None,
    ):
        if _info is None:
            # _top-level
            self.config_path = config_path
        else:
            self.subset = subset
        self.reset(
            subset=subset, _info=_info, verbose=verbose, _local_subsets=_local_subsets
        )

    def save_to_yaml(self, path, mode="w", exclude=["subset"]):
        # Write the current state of the class instance to a yaml file
        with open(path, mode) as file:
            _write_dict(_get_dict_exclude(self, exclude), file)

    def reset(self, subset="main", verbose=False, _info=None, _local_subsets=False):
        # Recreate class instance with the provided kwargs
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

    def update_reuse(self, st_str="${", en_str="}"):
        # By default, any config items with the format "${name}" will be filled using a higher-level instance of "name"
        # For example; if "seed: 0" and "subconfig.seed: ${seed}" then it becomes "subconfig.seed: 0"
        _process_reuse(self, self, st_str=st_str, en_str=en_str)

    def pop(self, key, default=None):
        return self.__dict__.pop(key, default)

    def __iter__(self):
        # Return the _top-level attribute names via 'for key in class_inst'
        for key in self.__dict__.keys():
            yield key

    def __setitem__(self, key, value):
        # Support setting values via 'class_inst["key"] = value'
        setattr(self, key, value)

    def __getitem__(self, key):
        # Support getting values via 'class_inst["key"]'
        return getattr(self, key)

    def get(self, key):
        return get_nested_attribute(self, key)  # self.__dict__.get(key, default)

    def set(self, key, value):
        _nested_set(self, key.split("."), value)

    def get_kwargs(self):
        return _get_dict_exclude(self)

    def print(self):
        dict_print(_get_dict_exclude(self))
        print()


def _try_float(obj):
    for k, v in obj.__dict__.items():
        # If the value is not already converted to a number
        if isinstance(v, str):
            try:
                tmp = float(v)
                if int(tmp) - tmp == 0:
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
    for k, v in source.__dict__.items():
        setattr(target, k, v)


def get_nested_attribute(obj, att_list):
    out = getattr(obj, att_list[0])
    for i in range(1, len(att_list)):
        out = getattr(out, att_list[i])
    return out


def _nested_set(obj, att_list, value):
    att = att_list[0]
    if isinstance(obj[att], args_from_YAML):
        _nested_set(obj[att], att_list[1:], value)
    else:
        setattr(obj, att, value)


def _process_reuse(
    data, original_data, st_str="${", en_str="}", ignore="???", max_depth=10
):
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
                print(
                    f'WARNING: AutoConfig could not find the following term for reuse: "{".".join(temp)}"'
                )
        elif isinstance(v, args_from_YAML):
            _process_reuse(v, original_data)
