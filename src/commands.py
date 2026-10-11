"""Shell commands operating on the in-memory VFS."""

import fnmatch
import getpass
import math
import posixpath
import time

BYTES_PER_UNIT = 1024
SIZE_UNITS = "KMGT"
DECIMAL_LIMIT = 10
DIRECTORY_MODE = "drwxr-xr-x"
FILE_MODE = "-rw-r--r--"
DATE_FORMAT = "%b %d %H:%M"
CURRENT_DIRECTORY = "."
LS_OPTIONS = "alh"
TOUCH_OPTIONS = "c"
FIND_PREDICATES = ("-name", "-type")
FIND_TYPES = ("f", "d")
HELP_TEXT = (
    ("cd [path]", "change the directory; no path or ~ means the root"),
    ("exit", "exit the emulator"),
    (
        "find [path...] [-name pattern] [-type f|d]",
        "print entries below the paths, filter by name or type",
    ),
    ("help", "show this list of commands"),
    (
        "ls [-a] [-l] [-h] [path]",
        "list a directory; -a hidden, -l long, -h readable sizes",
    ),
    ("tac file...", "print files with their lines in reverse order"),
    (
        "touch [-c] file...",
        "create empty files or update times; -c does not create",
    ),
)


def report(command, message):
    """Print an error message of the command and return False."""
    print(f"shell: {command}: {message}")
    return False


def expand_home(path):
    """Replace a leading ~ with the root of the VFS."""
    if path == "~":
        return "/"

    if path.startswith("~/"):
        return path[1:]

    return path


def split_options(args, allowed):
    """Split arguments into a set of short flags and operands.

    Flags may be combined (-la, -hla) and placed anywhere before
    the optional "--" separator. Unknown flags raise ValueError.
    """
    flags = set()
    operands = []
    only_operands = False

    for arg in args:
        if only_operands or arg == "-" or not arg.startswith("-"):
            operands.append(arg)
        elif arg == "--":
            only_operands = True
        else:
            flags.update(parse_flags(arg, allowed))

    return flags, operands


def parse_flags(arg, allowed):
    """Return the flag characters of one argument like -la."""
    for char in arg[1:]:
        if char not in allowed:
            raise ValueError(f"invalid option -- '{char}'")

    return set(arg[1:])


def format_size(size, human):
    """Format a size in bytes, optionally as 1.5K, 12M and so on."""
    if not human:
        return str(size)

    value = float(size)
    unit = ""

    for letter in SIZE_UNITS:
        if value < BYTES_PER_UNIT:
            break

        value /= BYTES_PER_UNIT
        unit = letter

    if not unit:
        return str(size)

    if value < DECIMAL_LIMIT:
        tenths = math.ceil(value * DECIMAL_LIMIT) / DECIMAL_LIMIT
        return f"{tenths:.1f}{unit}"

    return f"{math.ceil(value)}{unit}"


def format_long(name, node, size_text, width):
    """Format one entry of the long (-l) listing."""
    owner = getpass.getuser()
    mode = DIRECTORY_MODE if node.is_directory else FILE_MODE
    stamp = time.strftime(DATE_FORMAT, time.localtime(node.mtime))
    size = f"{size_text:>{width}}"
    return f"{mode} 1 {owner} {owner} {size} {stamp} {name}"


def format_entries(entries, flags):
    """Return the output lines for the listed (name, node) entries."""
    if "l" not in flags:
        return [name for name, _ in entries]

    sizes = [format_size(node.size, "h" in flags) for _, node in entries]
    width = max((len(size) for size in sizes), default=0)

    return [
        format_long(name, node, size, width)
        for (name, node), size in zip(entries, sizes)
    ]


def collect_entries(node, shown_name, flags):
    """Return the (name, node) pairs that ls shows for the node."""
    if not node.is_directory:
        return [(shown_name, node)]

    entries = [(child.name, child) for child in node.sorted_children()]

    if "a" not in flags:
        return [entry for entry in entries if not entry[0].startswith(".")]

    parent = node.parent or node
    return [(".", node), ("..", parent)] + entries


def execute_ls(args, vfs):
    """ls [-a] [-l] [-h] [path]: list a directory or a file."""
    try:
        flags, operands = split_options(args, LS_OPTIONS)
    except ValueError as error:
        return report("ls", error)

    if len(operands) > 1:
        return report("ls", "too many arguments")

    path = operands[0] if operands else ""
    node = vfs.resolve_path(expand_home(path))

    if node is None:
        return report(
            "ls",
            f"cannot access '{path}': No such file or directory"
        )

    entries = collect_entries(node, path, flags)

    for line in format_entries(entries, flags):
        print(line)

    return True


def execute_cd(args, vfs):
    """cd [path]: change the current directory."""
    if len(args) > 1:
        return report("cd", "too many arguments")

    path = expand_home(args[0] if args else "~")

    try:
        vfs.change_directory(path)
    except ValueError as error:
        return report("cd", error)

    return True


def parse_find(args):
    """Return the start paths and the predicates of a find command."""
    split = next(
        (i for i, arg in enumerate(args) if arg.startswith("-")),
        len(args)
    )
    paths = args[:split]
    options = {}
    tokens = iter(args[split:])

    for predicate in tokens:
        value = next(tokens, None)

        if predicate not in FIND_PREDICATES:
            raise ValueError(f"unknown predicate '{predicate}'")

        if value is None:
            raise ValueError(f"missing argument to '{predicate}'")

        if predicate == "-type" and value not in FIND_TYPES:
            raise ValueError(f"unknown argument to -type: '{value}'")

        options[predicate] = value

    return paths, options


def display_path(start, parts):
    """Build the printed path of an entry found below start."""
    if not parts:
        return start

    return "/".join([start.rstrip("/")] + parts)


def matches(shown, node, options):
    """Check an entry against the -name and -type predicates."""
    name = posixpath.basename(shown) or "/"
    pattern = options.get("-name")
    kind = options.get("-type")

    if pattern is not None and not fnmatch.fnmatchcase(name, pattern):
        return False

    if kind == "f":
        return not node.is_directory

    if kind == "d":
        return node.is_directory

    return True


def find_in(start, options, vfs):
    """Print the matching entries below one start path."""
    node = vfs.resolve_path(expand_home(start))

    if node is None:
        return report("find", f"'{start}': No such file or directory")

    for parts, found in vfs.walk(node):
        shown = display_path(start, parts)

        if matches(shown, found, options):
            print(shown)

    return True


def execute_find(args, vfs):
    """find [path...] [-name pattern] [-type f|d]: search entries."""
    try:
        paths, options = parse_find(args)
    except ValueError as error:
        return report("find", error)

    success = True

    for start in paths or [CURRENT_DIRECTORY]:
        success = find_in(start, options, vfs) and success

    return success


def tac_file(path, vfs):
    """Print the lines of one file in reverse order."""
    node = vfs.resolve_path(expand_home(path))

    if node is None:
        return report("tac", f"{path}: No such file or directory")

    if node.is_directory:
        return report("tac", f"{path}: Is a directory")

    text = node.content.decode("utf-8", errors="backslashreplace")

    for line in reversed(text.splitlines()):
        print(line)

    return True


def execute_tac(args, vfs):
    """tac file...: print files with their lines reversed."""
    try:
        _, operands = split_options(args, "")
    except ValueError as error:
        return report("tac", error)

    if not operands:
        return report("tac", "missing file operand")

    success = True

    for path in operands:
        success = tac_file(path, vfs) and success

    return success


def touch_file(path, create, vfs):
    """Touch one file and report the error if it fails."""
    try:
        vfs.touch(expand_home(path), create)
    except ValueError as error:
        return report("touch", error)

    return True


def execute_touch(args, vfs):
    """touch [-c] file...: create files or update their times."""
    try:
        flags, operands = split_options(args, TOUCH_OPTIONS)
    except ValueError as error:
        return report("touch", error)

    if not operands:
        return report("touch", "missing file operand")

    success = True

    for path in operands:
        success = touch_file(path, "c" not in flags, vfs) and success

    return success


def execute_help(args, vfs):
    """help: print the list of commands with descriptions."""
    if args:
        return report("help", "too many arguments")

    print("Available commands:")

    for usage, description in HELP_TEXT:
        print(f"  {usage}")
        print(f"      {description}")

    return True


COMMANDS = {
    "cd": execute_cd,
    "find": execute_find,
    "help": execute_help,
    "ls": execute_ls,
    "tac": execute_tac,
    "touch": execute_touch,
}
