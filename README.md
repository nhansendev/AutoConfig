# AutoConfig
A python utility for reading/writing custom YAML configuration files

# Requirements
- pyyaml
- Python 3.6+ (not tested with earlier versions)

# Installation
From within the AutoConfig folder:

```
pip install .
```

To uninstall:

```
pip uninstall AutoConfig
```

# Usage
## > YAML file formatting (see included example.yaml)
- All config info exists as key:value pairs, which can be nested using indentation
- Recognizes:
    - floats/ints
    - lists of values: `[0.1, -1.1, 3]` etc.
    - scientific notation: `1.1e-5`
    - `None`: specified as `null`
    - Setting placeholders for later update: `norm: ${norm}` (see `.update_reuse`)
    - booleans
    - Everything is a string otherwise
- Python comments are ignored: `# like this`

## > args_from_YAML
The main class for reading/writing/printing from YAML config files
### Configuration:
path | *str*
> The path to the YAML file

subset | *iterable of str, default=None*:
> An optional iterable of keys within the file to read, ignoring others

verbose | *bool, default=False*
> Provides some info about the config being used

### Functions
.reset(subset=["main"])
> Re-loads the config from the originally provided path, if available

> subset(s) can optionally be specified

.save_to_yaml(path, mode='w', exclude=["subset"])
> Writes the current state of the class and its data to a yaml file

> Optionally exclude subsets

.update_reuse(st_str="${", en_str="}", ignore="???", max_depth=10):
> By default, any config items with the format "${name}" will be filled using a higher-level instance of "name"

> For example; if "seed: 0" and "subconfig.seed: ${seed}" then it becomes "subconfig.seed: 0"

> Additionally, any config items specified with the `ignore` value will not be propagated.

> For example; if "seed: ???" and "subconfig.seed: ${seed}" then it remains "subconfig.seed: ${seed}"

### Setting/Getting
- Any config values (including nested) can be accessed via the format `class_instance.key1.key2.key3`
- The class functions as an iterator (`__iter__`), yielding any keys
- `.pop(key)` removes a given key (if available) and returns its matching value
- Supports setting values via `class_inst["key"] = value`, including nested values `class_inst["key"]["key2"]["key3"] = value`
- Supports getting values via `class_inst["key"]`, including nested values `class_inst["key"]["key2"]["key3"]`
- `.get(keys)` takes an iterable of keys and returns the value at the end of the key chain, if available
- `.set(keys)` takes an iterable of keys and sets the value at the end of the key chain, if available
- `.get_dict()` returns a dictionary representation of the current configuration
- `.print()` uses DictionaryPrint to create a clean print of the data


### Usage Example:

    from AutoConfig import args_from_YAML
    
    A = args_from_YAML(<config file path>, verbose=True)
    A.update_reuse()
    
    print(A.STE_cfg.noise_penalty)
    print(A["DAAC_cfg"]["clip_param"])
    
    A.print()

### Result:
    AutoConfig using: /home/user/Desktop/example.yaml, subset: None
    
    0.001
    0.2

    config_path: /home/user/Desktop/example.yaml
    ______ seed: 0
    _ save_path: /home/user/Desktop/Results/
    ____ device: cpu
    __ data_dir: /home/user/Desktop/DataSets/
    window_size: 128
    ______ mode: debug
    ______ norm: None
    __ ENV_info:
               > __ input_dim: None
               > __ state_dim: None
               > _ action_dim: None
               > action_space: None
               > __ obs_shape: None
    ___ STE_cfg:
               > _________ seed: 0
               > _________ mode: debug
               > _________ norm: None
               > ____ save_path: /home/user/Desktop/Results/
               > __ window_size: 128
               > ___ stats_path: None
               > __________ kwd: None
               > _____ max_loss: None
               > _______ repeat: None
               >  noise_penalty: 0.001
               > data_divisions: [0.9, 0.1]
               > __ action_mode: soft
               > ______ deadlim: [0.1, 0.1]
    __ DAAC_cfg:
               > ____________ seed: 0
               > __________ device: cpu
               > ________ env_name: STEnv
               > ______________ lr: 0.0005
               > _____________ eps: 1e-05
               > ___________ alpha: 0.99
               > ___________ gamma: 0.999
               > ______ gae_lambda: 0.95
               > ____ entropy_coef: 0.01
               > _ value_loss_coef: 0.5
               > ___ max_grad_norm: 0.5
               > ___ num_processes: 16
               > _______ num_steps: 256
               > _______ ppo_epoch: 1
               > __ num_mini_batch: 8
               > ______ clip_param: 0.2
               > ____ log_interval: 10
               > ___ num_env_steps: 2500
               > ____________ algo: idaac
               > _____ hidden_size: 256
               > _________ log_dir: /home/user/Desktop/Results/
               > _______ save_path: /home/user/Desktop/Results/
               > _____ value_epoch: 9
               > ______ value_freq: 1
               > ___ adv_loss_coef: 0.25
               > use_nonlinear_clf: False
               > _ clf_hidden_size: 4
    

## > reassign(target, source)
A simple function for copying key:value attributes from one object to another

Useful for loading your config into a class without passing everything as kwargs

### Example Usage:
    from AutoConfig import reassign

    my_class = dummy_class()
    
    A = args_from_YAML(path)
    print(A.save_path) # exists
    
    print(my_class.save_path) # does not exist
    
    reassign(my_class, A) # copy config info into "my_class"
    print(my_class.save_path) # exists
