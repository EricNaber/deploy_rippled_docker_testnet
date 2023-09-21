import argh, yaml, os, shutil


RIPPLED_IMAGE_HONEST = "xrpllabsofficial/xrpld"
RIPPLED_IMAGE_MALICIOUS = "xrpllabsofficial/xrpld"


def get_vars_from_input(input_path: str, number_nodes: int) -> list:
    # Read the first number_nodes entries from input_path as yml-format and return it
    print(f"Read data from {input_path} and take first {number_nodes} nodes")
    with open(input_path, "r") as input_file:
        result = yaml.safe_load(input_file.read())
    return result[0:number_nodes]


def _get_validator_fixed_ips(validator: dict, validators: list):
    # each validator has section '[ips_fixed]'. This function creates its content and return it as a string
    fixed_ips_string = ""
    validators_list = validator["unl"]   # Store all validators accepted
    for entry in validators:
        if entry["name"] in validators_list:
            fixed_ips_string += f"{entry['name']} 51235\n"
    return fixed_ips_string


def _wipe_directory(path: str) -> None:
    shutil.rmtree(path)
    os.mkdir(path)


def _map_validator_names_to_pubkeys(validators: list):
    # Create a dictionary from 
    mapping = {}
    try:
        for validator in validators:
            mapping[validator['name']] = validator['public_key']
    except BaseException:
        print("Soemthing went wrong. Are all UNLs defined correctly?")
    return mapping


def create_validator_folders(output_path: str, validators: list) -> None:
    """
    This function creates all needed configuration-files for each validation node.
    It first wipes the output-path and then provisions it again. All information is derived from validators.
    """
    _wipe_directory(output_path)    # Clear output_path before creating files and folders
    validator_to_pubkeys = _map_validator_names_to_pubkeys(validators)
    
    for validator in validators:    
        # Create folders for every validator
        validator_dir = os.path.join(output_path, validator["name"])
        validator_config_path = os.path.join(output_path, validator["name"], "config")
        
        os.mkdir(validator_dir)
        os.mkdir(validator_config_path)

        # Create rippled.cfg file
        with open(os.path.join("templates", "rippled.cfg.temp"), "r") as template_file:
            template_string = template_file.read()

        template_string = template_string.replace("$(validator_token)", validator["token"])
        template_string = template_string.replace("$(validator_fixed_ips)", _get_validator_fixed_ips(validator, validators))
        
        with open(os.path.join(validator_config_path, "rippled.cfg"), "w") as file:
            file.write(template_string)

        # Create validators.cfg (UNLs for each validator)       
        validator_pubkeys_string = "[validators]\n"
        for entry in validator['unl']:
            validator_pubkeys_string += f"    {validator_to_pubkeys[entry]}\n"
        with open(os.path.join(validator_config_path, "validators.txt"), "w") as file:
            file.write(validator_pubkeys_string)


def create_docker_compose_file(validators: list, output_path: str) -> None:
    last_used_ports = {"port1": 8001, "port2": 5006, "port3": 4001, "port4": 9001}
    with open(os.path.join("templates", "docker-compose-validator.yml.temp"), "r") as template_file:
        validator_template_string = template_file.read()
    with open(os.path.join("templates", "docker-compose.yml.temp"), "r") as template_file:
        docker_compose_template_string = template_file.read()

    validators_string = ""
    for validator in validators:
        validator_string: str = validator_template_string
        validator_string = validator_string.replace("$(validator_name)", validator["name"])
        
        last_used_ports["port1"] += 1
        last_used_ports["port2"] += 1
        last_used_ports["port3"] += 1
        last_used_ports["port4"] += 1
        validator_string = validator_string.replace("$(validator_port1)", str(last_used_ports["port1"]))
        validator_string = validator_string.replace("$(validator_port2)", str(last_used_ports["port2"]))
        validator_string = validator_string.replace("$(validator_port3)", str(last_used_ports["port3"]))
        validator_string = validator_string.replace("$(validator_port4)", str(last_used_ports["port4"]))

        if validator["name"] == "validator_00":
            validator_string = validator_string.replace("$(validator_image)", RIPPLED_IMAGE_MALICIOUS)
        else:
            validator_string = validator_string.replace("$(validator_image)", RIPPLED_IMAGE_HONEST)
        
        validators_string += f"{validator_string}\n\n"
    
    with open(os.path.join(output_path, "docker-compose.yml"), "w") as file:
        docker_compose_string = docker_compose_template_string.replace("$(validators_string)", validators_string)
        file.write(docker_compose_string)





@argh.arg('input_path',help="Input path to validator-information")
@argh.arg('output_path',help="Path to output validator-configs and file structure")
@argh.arg('number_nodes',help="Number of nodes that shall be created. (creates 1 malicious node, n-1 honest nodes)", type=int)
def main(input_path, output_path, number_nodes):
    validators = get_vars_from_input(input_path, number_nodes)
    create_validator_folders(output_path, validators)
    create_docker_compose_file(validators, output_path)


if __name__=="__main__":
    try:
        argh.dispatch_command(main)
    except BaseException as err:
        print(f"Something went wrong: {err}")