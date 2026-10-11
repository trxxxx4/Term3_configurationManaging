"""Entry point of the UNIX-like shell emulator."""

import argparse
import getpass
import shlex
import socket
import sys
import tomllib

from commands import COMMANDS
from vfs import VFS


def get_prompt(vfs):
    """Build the prompt from the real user and host names."""
    username = getpass.getuser()
    hostname = socket.gethostname()
    path = vfs.get_path()

    if path == "/":
        path = "~"
    else:
        path = "~" + path

    return f"{username}@{hostname}:{path}$ "


def parse_input(user_input):
    """Split a command line, honouring quoted arguments."""
    try:
        return shlex.split(user_input)
    except ValueError as error:
        print(f"shell: syntax error: {error}")
        return None


def parse_arguments():
    """Parse the command line parameters."""
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
    """Read the TOML configuration file."""
    try:
        with open(config_path, "rb") as config_file:
            return tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        print(f"shell: config error: {error}")
        return None


def get_config_value(config, name):
    """Return a required string parameter of the config."""
    value = config.get(name)

    if not isinstance(value, str):
        raise ValueError(
            f"configuration parameter '{name}' is missing"
        )

    return value


def resolve_settings(arguments, config):
    """Merge command line and config; CLI has priority."""
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
    """Print the effective configuration."""
    print("Emulator configuration:")
    print(f"VFS path: {vfs_path}")
    print(f"Startup script: {startup_script}")
    print(f"Config file: {config_path}")
    print()


def execute_command(command, args, vfs):
    """Run a command; return (success, should_exit)."""
    if command == "exit":
        return True, True

    handler = COMMANDS.get(command)

    if handler is None:
        print(f"shell: command not found: {command}")
        return False, False

    return handler(args, vfs), False


def execute_line(user_input, vfs):
    """Parse and execute one command line."""
    tokens = parse_input(user_input)

    if tokens is None:
        return False, False

    if not tokens:
        return True, False

    return execute_command(
        tokens[0],
        tokens[1:],
        vfs
    )


def run_startup_script(script_path, vfs):
    """Run the startup script and stop at the first error."""
    try:
        with open(
            script_path,
            "r",
            encoding="utf-8"
        ) as script:
            for line in script:
                command = line.strip()

                if not command:
                    continue

                print(f"{get_prompt(vfs)}{command}")

                success, should_exit = execute_line(
                    command,
                    vfs
                )

                if not success:
                    print(
                        "shell: startup script execution failed"
                    )
                    return False, False

                if should_exit:
                    return True, True

    except OSError as error:
        print(f"shell: startup script error: {error}")
        return False, False

    return True, False


def echo_piped_input(user_input):
    """Show the typed command when input comes from a pipe or file."""
    if not sys.stdin.isatty():
        print(user_input)


def run_repl(vfs):
    """Read and execute commands until exit, Ctrl-C or end of input."""
    while True:
        try:
            user_input = input(get_prompt(vfs))
        except (EOFError, KeyboardInterrupt):
            print("\nexit")
            break

        echo_piped_input(user_input)

        if not user_input.strip():
            continue

        _, should_exit = execute_line(user_input, vfs)

        if should_exit:
            break


def load_vfs(vfs_path):
    """Load the VFS from an XML file."""
    try:
        return VFS.from_xml(vfs_path)
    except ValueError as error:
        print(f"shell: VFS error: {error}")
        return None


def run_application(startup_script, vfs):
    """Run the startup script and then the REPL."""
    startup_success, should_exit = run_startup_script(
        startup_script,
        vfs
    )

    if not startup_success:
        return 1

    if should_exit:
        return 0

    run_repl(vfs)
    return 0


def main():
    """Start the emulator and return the exit code."""
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

    vfs = load_vfs(vfs_path)
    if vfs is None:
        return 1

    return run_application(startup_script, vfs)


if __name__ == "__main__":
    raise SystemExit(main())