import fnmatch
import math

LS_FLAGS = "alh"
MAX_LS_PATHS = 1
MAX_CD_ARGS = 1
BLOCK_SIZE = 1024
SIZE_UNITS = "KMGTPE"
LAST_UNIT = len(SIZE_UNITS) - 1
TENTHS = 10
SHORT_LIMIT = 10
DIRECTORY_MODE = "drwxr-xr-x"
FILE_MODE = "-rw-r--r--"
FIND_OPTIONS = ("-name", "-type")
FIND_TYPES = {"f": False, "d": True}


def parse_ls_flags(argument):
    """Return the set of ls flags from an argument like '-lah'."""
    letters = argument[1:]

    for letter in letters:
        if letter not in LS_FLAGS:
            raise ValueError(f"invalid option -- '{letter}'")

    return set(letters)


def parse_ls_args(args):
    """Split ls arguments into a set of flags and a list of paths."""
    flags = set()
    paths = []
    options_ended = False

    for argument in args:
        if options_ended:
            paths.append(argument)
        elif argument == "--":
            options_ended = True
        elif argument.startswith("-") and argument != "-":
            flags.update(parse_ls_flags(argument))
        else:
            paths.append(argument)

    return flags, paths


def format_size(size, human):
    """Format a size in bytes, as 'ls -h' does when human is True."""
    if not human or size < BLOCK_SIZE:
        return str(size)

    index = 0
    value = size / BLOCK_SIZE

    while value >= BLOCK_SIZE and index < LAST_UNIT:
        value /= BLOCK_SIZE
        index += 1

    rounded = math.ceil(value * TENTHS) / TENTHS

    if rounded < SHORT_LIMIT:
        return f"{rounded:.1f}{SIZE_UNITS[index]}"

    return f"{math.ceil(value)}{SIZE_UNITS[index]}"


def sort_key(item):
    """Return the ls sorting key for a (name, node) pair."""
    return item[0].lower(), item[0]


def collect_entries(vfs, path, show_all):
    """Return the (name, node) pairs that ls has to print."""
    node = vfs.current if path is None else vfs.resolve_path(path)

    if node is None:
        raise ValueError(f"path not found: {path}")

    if not node.is_directory:
        return [(path, node)]

    entries = [
        (child.name, child)
        for child in node.children
        if show_all or not child.name.startswith(".")
    ]
    entries.sort(key=sort_key)

    if show_all:
        parent = node.parent or node
        entries = [(".", node), ("..", parent)] + entries

    return entries


def format_ls_lines(entries, long_format, human):
    """Build output lines for ls in short or long (-l) format."""
    if not long_format:
        return [name for name, _ in entries]

    sizes = [format_size(node.size, human) for _, node in entries]
    width = max((len(size) for size in sizes), default=0)
    lines = []

    for (name, node), size in zip(entries, sizes):
        mode = DIRECTORY_MODE if node.is_directory else FILE_MODE
        lines.append(f"{mode} {size:>{width}} {name}")

    return lines


def execute_ls(args, vfs):
    """ls [-a] [-l] [-h] [path]: list directory contents."""
    try:
        flags, paths = parse_ls_args(args)

        if len(paths) > MAX_LS_PATHS:
            raise ValueError("too many arguments")

        path = paths[0] if paths else None
        entries = collect_entries(vfs, path, "a" in flags)
    except ValueError as error:
        print(f"shell: ls: {error}")
        return False, False

    for line in format_ls_lines(entries, "l" in flags, "h" in flags):
        print(line)

    return True, False


def execute_cd(args, vfs):
    """cd [path]: change the current VFS directory."""
    if len(args) > MAX_CD_ARGS:
        print("shell: cd: too many arguments")
        return False, False

    path = args[0] if args else "~"

    if path == "~":
        path = "/"

    try:
        vfs.change_directory(path)
    except ValueError as error:
        print(f"shell: cd: {error}")
        return False, False

    return True, False


def join_path(parent, name):
    """Join a displayed directory path and an entry name."""
    if parent.endswith("/"):
        return parent + name

    return f"{parent}/{name}"


def base_name(path):
    """Return the last component of a displayed path."""
    stripped = path.rstrip("/")

    if not stripped:
        return "/"

    return stripped.rsplit("/", 1)[-1]


def walk(node, display):
    """Yield (displayed path, node) for a node and its descendants."""
    yield display, node

    if node.is_directory:
        for child in sorted(node.children, key=lambda c: c.name):
            yield from walk(child, join_path(display, child.name))


def parse_find_options(rest):
    """Parse find predicates into a dict like {'-name': '*.txt'}."""
    options = {}
    index = 0

    while index < len(rest):
        option = rest[index]

        if option not in FIND_OPTIONS:
            raise ValueError(f"unknown argument: {option}")

        if index + 1 >= len(rest):
            raise ValueError(f"missing argument to '{option}'")

        options[option] = rest[index + 1]
        index += 2

    return options


def parse_find_args(args):
    """Return (path, name pattern, type letter) for find."""
    path = "."
    rest = list(args)

    if rest and not rest[0].startswith("-"):
        path = rest.pop(0)

    options = parse_find_options(rest)
    type_letter = options.get("-type")

    if type_letter is not None and type_letter not in FIND_TYPES:
        raise ValueError(f"unknown argument to -type: {type_letter}")

    return path, options.get("-name"), type_letter


def matches(display, node, pattern, type_letter):
    """Check a node against the -name and -type predicates."""
    if pattern is not None:
        if not fnmatch.fnmatchcase(base_name(display), pattern):
            return False

    if type_letter is not None:
        return node.is_directory == FIND_TYPES[type_letter]

    return True


def execute_find(args, vfs):
    """find [path] [-name pattern] [-type f|d]: search the VFS."""
    try:
        path, pattern, type_letter = parse_find_args(args)
        start = vfs.resolve_path(path)

        if start is None:
            raise ValueError(f"path not found: {path}")
    except ValueError as error:
        print(f"shell: find: {error}")
        return False, False

    for display, node in walk(start, path):
        if matches(display, node, pattern, type_letter):
            print(display)

    return True, False


def print_reversed(content):
    """Print the lines of a bytes object in reverse order."""
    text = content.decode("utf-8", errors="replace")

    for line in reversed(text.splitlines()):
        print(line)


def execute_tac(args, vfs):
    """tac file...: print file lines in reverse order."""
    if not args:
        print("shell: tac: missing file operand")
        return False, False

    success = True

    for path in args:
        try:
            print_reversed(vfs.read_file(path))
        except ValueError as error:
            print(f"shell: tac: {error}")
            success = False

    return success, False


COMMANDS = {
    "ls": execute_ls,
    "cd": execute_cd,
    "find": execute_find,
    "tac": execute_tac,
}


def execute_command(command, args, vfs):
    """Run a command; return (success, should_exit)."""
    if command == "exit":
        return True, True

    handler = COMMANDS.get(command)

    if handler is None:
        print(f"shell: command not found: {command}")
        return False, False

    return handler(args, vfs)
