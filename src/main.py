import argparse
import getpass
import shlex
import socket
import tomllib


def get_prompt():
    username = getpass.getuser()
    hostname = socket.gethostname()
    return f"{username}@{hostname}:~$ "


def parse_input(user_input):
    try:
        return shlex.split(user_input)
    except ValueError as error:
        print(f"shell: syntax error: {error}")
        return None


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="UNIX-like shell emulator"
    )

    parser.add_argument(
        "--vfs-path",
        help="path to the VFS"
    )

    parser.add_argument(
        "--startup-script",
        help="path to the startup script"
    )

    parser.add_argument(
        "--config",
        required=True,
        help="path to the TOML configuration file"
    )

    return parser.parse_args()


def load_config(config_path):
    try:
        with open(config_path, "rb") as config_file:
            return tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        print(f"shell: config error: {error}")
        return None


def get_config_value(config, name):
    value = config.get(name)

    if not isinstance(value, str):
        raise ValueError(
            f"configuration parameter '{name}' is missing"
        )

    return value


def resolve_settings(arguments, config):
    try:
        vfs_path = arguments.vfs_path
        startup_script = arguments.startup_script

        if vfs_path is None:
            vfs_path = get_config_value(config, "vfs_path")

        if startup_script is None:
            startup_script = get_config_value(
                config,
                "startup_script"
            )

        return vfs_path, startup_script

    except ValueError as error:
        print(f"shell: config error: {error}")
        return None


def print_settings(vfs_path, startup_script, config_path):
    print("Emulator configuration:")
    print(f"VFS path: {vfs_path}")
    print(f"Startup script: {startup_script}")
    print(f"Config file: {config_path}")
    print()


def execute_command(command, args):
    if command == "exit":
        return True, True

    if command in ("ls", "cd"):
        print(
            f"Executing command '{command}' with args: {args}"
        )
        return True, False

    print(f"shell: command not found: {command}")
    return False, False


def execute_line(user_input):
    tokens = parse_input(user_input)

    if tokens is None:
        return False, False

    if not tokens:
        return True, False

    return execute_command(tokens[0], tokens[1:])


def run_startup_script(script_path):
    try:
        with open(script_path, "r", encoding="utf-8") as script:
            for line in script:
                command = line.strip()

                if not command:
                    continue

                print(f"{get_prompt()}{command}")

                success, should_exit = execute_line(command)

                if not success:
                    print("shell: startup script execution failed")
                    return False, False

                if should_exit:
                    return True, True

    except OSError as error:
        print(f"shell: startup script error: {error}")
        return False, False

    return True, False


def run_repl():
    while True:
        try:
            user_input = input(get_prompt())

            if not user_input.strip():
                continue

            success, should_exit = execute_line(user_input)

            if should_exit:
                break

        except KeyboardInterrupt:
            print("\nexit")
            break


def main():
    arguments = parse_arguments()

    config = load_config(arguments.config)

    if config is None:
        return 1

    settings = resolve_settings(arguments, config)

    if settings is None:
        return 1

    vfs_path, startup_script = settings

    print_settings(
        vfs_path,
        startup_script,
        arguments.config
    )

    startup_success, should_exit = run_startup_script(
        startup_script
    )

    if not startup_success:
        return 1

    if should_exit:
        return 0

    run_repl()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())