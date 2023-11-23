# AutoConfig
A python utility for reading custom YAML configuration files

# Requirements
- pyyaml
- DictionaryPrint (https://github.com/nhansendev/DictionaryPrint)
- Python 3.6+ (not tested with earlier versions)

# Usage
## args_from_YAML
The main class for reading/writing/printing from YAML config files
### Configuration:
path | *str*
> The path to the YAML file

subset | *iterable of str, default=None*:
> An iterable of subsets within the file to read, ignoring others

verbose | *bool, default=False*
> Provides some info about the config being used

### Functions
.reset(subset=["main"])
> Re-loads the config from the originally provided path, if available

> subset(s) can optionally be specified

.save_to_yaml(path, mode='w', exclude=["subset"])
> Writes the current state of the class and its data to file

> Optionally exclude subsets

.update_reuse(st_str="${", en_str="}", ignore="???", max_depth=10):
> By default, any config items with the format "${name}" will be filled using a higher-level instance of "name"

> For example; if "seed: 0" and "subconfig.seed: ${seed}" then it becomes "subconfig.seed: 0"

> Additionally, any config items specified with the `ignore` value will not be propagated.

> For example; if "seed: ???" and "subconfig.seed: ${seed}" then it remains "subconfig.seed: ${seed}"

### Setting/Getting
The class functions as an iterator ('__iter__'), yielding any attribute keys

".pop(key)" removes a given key (if available) and returns its matching value

Supports setting values via 'class_inst["key"] = value'

Supports getting values via 'class_inst["key"]'

".get(keys)" takes an iterable of keys and returns the value at the end of the key chain, if available

".set(keys)" takes an iterable of keys and sets the value at the end of the key chain, if available

".get_dict()" returns a dictionary representation of the current configuration

".print()" uses DictionaryPrint to create a clean print of the data


### Usage Example:

    from AutoConfig import args_from_YAML
    
    A = args_from_YAML(<config file path>, verbose=True)
    A.update_reuse()
    A.print()

  
