import base64
import binascii
import xml.etree.ElementTree as ET


class VFSNode:
    def __init__(self, name, is_directory, parent=None, content=b""):
        self.name = name
        self.is_directory = is_directory
        self.parent = parent
        self.content = content
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def get_child(self, name):
        for child in self.children:
            if child.name == name:
                return child

        return None


class VFS:
    def __init__(self, root):
        self.root = root
        self.current = root

    @classmethod
    def from_xml(cls, path):
        tree = cls._parse_xml(path)
        root_element = cls._validate_root(tree)
        root = VFSNode("", True)
        cls._load_root_nodes(root_element, root)
        return cls(root)

    @staticmethod
    def _parse_xml(path):
        try:
            return ET.parse(path)
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

    @staticmethod
    def _validate_root(tree):
        root_element = tree.getroot()

        if root_element.tag != "vfs":
            raise ValueError(
                "invalid VFS XML: root element must be 'vfs'"
            )

        return root_element

    @classmethod
    def _load_root_nodes(cls, root_element, root):
        try:
            for element in root_element:
                cls._load_node(element, root)
        except ValueError:
            raise
        except (binascii.Error, ValueError) as error:
            raise ValueError(
                f"invalid VFS data: {error}"
            ) from error

    @classmethod
    def _load_node(cls, element, parent):
        if element.tag == "directory":
            return cls._load_directory(element, parent)

        if element.tag == "file":
            return cls._load_file(element, parent)

        raise ValueError(
            f"invalid VFS element: {element.tag}"
        )

    @classmethod
    def _load_directory(cls, element, parent):
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
        for child in element:
            if child.tag not in ("directory", "file"):
                raise ValueError(
                    f"invalid VFS element: {child.tag}"
                )

    @classmethod
    def _load_file(cls, element, parent):
        name = cls._get_name(element)
        content = cls._decode_file_content(element, name)

        if list(element):
            raise ValueError(
                f"file '{name}' cannot contain child elements"
            )

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
        if parent.get_child(name) is not None:
            raise ValueError(
                f"duplicate VFS entry: {name}"
            )

    def get_path(self, node=None):
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

    def list_directory(self, path=None):
        if path is None:
            node = self.current
        else:
            node = self.resolve_path(path)

        if node is None:
            raise ValueError(
                f"path not found: {path}"
            )

        if not node.is_directory:
            raise ValueError(
                f"not a directory: {path}"
            )

        return node.children