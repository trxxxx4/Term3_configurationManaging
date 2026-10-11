"""In-memory virtual file system loaded from an XML file."""

import base64
import binascii
import posixpath
import time
import xml.etree.ElementTree as ET

DIRECTORY_SIZE = 4096


class VFSNode:
    """A file or a directory of the virtual file system."""

    def __init__(
        self,
        name,
        is_directory,
        parent=None,
        content=b"",
    ):
        """Create a node; the modification time is the current time."""
        self.name = name
        self.is_directory = is_directory
        self.parent = parent
        self.content = content
        self.children = []
        self.mtime = time.time()

    @property
    def size(self):
        """Return the size of the node in bytes."""
        if self.is_directory:
            return DIRECTORY_SIZE

        return len(self.content)

    def add_child(self, child):
        """Attach a child node."""
        self.children.append(child)

    def get_child(self, name):
        """Return the child with the given name or None."""
        for child in self.children:
            if child.name == name:
                return child

        return None

    def sorted_children(self):
        """Return children sorted by name."""
        return sorted(
            self.children,
            key=lambda child: (child.name.lower(), child.name)
        )


class VFS:
    """Virtual file system with a current working directory."""

    def __init__(self, root):
        """Create a VFS with the given root node."""
        self.root = root
        self.current = root

    @classmethod
    def from_xml(cls, path):
        """Build a VFS from an XML file."""
        try:
            tree = ET.parse(path)
        except FileNotFoundError as error:
            raise ValueError(
                f"VFS file not found: {path}"
            ) from error
        except ET.ParseError as error:
            raise ValueError(
                f"invalid VFS XML: {error}"
            ) from error
        except OSError as error:
            raise ValueError(
                f"cannot read VFS file: {error}"
            ) from error

        root_element = tree.getroot()

        if root_element.tag != "vfs":
            raise ValueError(
                "invalid VFS XML: root element must be 'vfs'"
            )

        root = VFSNode("", True)

        try:
            for element in root_element:
                cls._load_node(element, root)
        except (binascii.Error, ValueError) as error:
            raise ValueError(
                f"invalid VFS data: {error}"
            ) from error

        return cls(root)

    @classmethod
    def _load_node(cls, element, parent):
        """Load a directory or a file element."""
        if element.tag == "directory":
            return cls._load_directory(element, parent)

        if element.tag == "file":
            return cls._load_file(element, parent)

        raise ValueError(
            f"invalid VFS element: {element.tag}"
        )

    @classmethod
    def _load_directory(cls, element, parent):
        """Load a directory element with its children."""
        name = cls._get_name(element)
        cls._validate_directory_children(element)

        node = VFSNode(
            name=name,
            is_directory=True,
            parent=parent
        )
        cls._check_duplicate(parent, name)
        parent.add_child(node)

        for child in element:
            cls._load_node(child, node)

        return node

    @staticmethod
    def _validate_directory_children(element):
        """Check the tags of directory children."""
        for child in element:
            if child.tag not in ("directory", "file"):
                raise ValueError(
                    f"invalid VFS element: {child.tag}"
                )

    @classmethod
    def _load_file(cls, element, parent):
        """Load a file element."""
        name = cls._get_name(element)

        if list(element):
            raise ValueError(
                f"file '{name}' cannot contain child elements"
            )

        content = cls._decode_file_content(element, name)
        node = VFSNode(
            name=name,
            is_directory=False,
            parent=parent,
            content=content
        )
        cls._check_duplicate(parent, name)
        parent.add_child(node)
        return node

    @staticmethod
    def _decode_file_content(element, name):
        """Decode plain or base64 file content."""
        encoding = element.get("encoding")
        content = element.text or ""

        if encoding == "base64":
            try:
                return base64.b64decode(
                    "".join(content.split()),
                    validate=True
                )
            except binascii.Error as error:
                raise ValueError(
                    f"invalid base64 data in file '{name}'"
                ) from error

        if encoding is not None:
            raise ValueError(
                f"unsupported encoding '{encoding}' "
                f"for file '{name}'"
            )

        return content.encode("utf-8")

    @staticmethod
    def _get_name(element):
        """Return a valid entry name of an element."""
        name = element.get("name")

        if not name:
            raise ValueError(
                f"{element.tag} name is missing"
            )

        if "/" in name or name in (".", ".."):
            raise ValueError(
                f"invalid {element.tag} name: {name}"
            )

        return name

    @staticmethod
    def _check_duplicate(parent, name):
        """Reject two entries with the same name."""
        if parent.get_child(name) is not None:
            raise ValueError(
                f"duplicate VFS entry: {name}"
            )

    def get_path(self, node=None):
        """Return the absolute path of a node."""
        if node is None:
            node = self.current

        if node is self.root:
            return "/"

        parts = []

        while node is not self.root:
            parts.append(node.name)
            node = node.parent

        parts.reverse()
        return "/" + "/".join(parts)

    def resolve_path(self, path):
        """Return the node for a path or None if it is missing."""
        if path == "":
            return self.current

        if path.startswith("/"):
            node = self.root
            parts = path.split("/")[1:]
        else:
            node = self.current
            parts = path.split("/")

        for part in parts:
            if not part or part == ".":
                continue

            if part == "..":
                if node.parent is not None:
                    node = node.parent
                continue

            child = node.get_child(part)

            if child is None:
                return None

            node = child

        return node

    def change_directory(self, path):
        """Make a directory the current one."""
        node = self.resolve_path(path)

        if node is None:
            raise ValueError(
                f"directory not found: {path}"
            )

        if not node.is_directory:
            raise ValueError(
                f"not a directory: {path}"
            )

        self.current = node

    def walk(self, node):
        """Yield (relative name parts, node) depth-first, node first."""
        yield [], node

        if node.is_directory:
            for child in node.sorted_children():
                for parts, found in self.walk(child):
                    yield [child.name] + parts, found

    def touch(self, path, create=True):
        """Update the mtime of an entry, creating a file if needed."""
        node = self.resolve_path(path)

        if node is not None:
            node.mtime = time.time()
            return

        if create:
            self._create_file(path)

    def _create_file(self, path):
        """Create an empty file in an existing directory."""
        error = f"cannot touch '{path}'"

        if path.endswith("/"):
            raise ValueError(f"{error}: No such file or directory")

        parent_path, name = posixpath.split(path)
        parent = self.resolve_path(parent_path)

        if parent is None:
            raise ValueError(f"{error}: No such file or directory")

        if not parent.is_directory:
            raise ValueError(f"{error}: Not a directory")

        parent.add_child(VFSNode(name, False, parent))
        parent.mtime = time.time()
