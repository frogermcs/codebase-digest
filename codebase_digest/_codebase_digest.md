# Codebase Analysis for: 

## Directory Structure

```
└── 
    ├── core
    │   ├── models.py (3617 bytes)
    │   ├── codebase_analysis.py (3214 bytes)
    │   └── ignore_patterns_manager.py (3144 bytes)
    ├── output_formatter.py (4307 bytes)
    ├── tests
    │   ├── test_codebase_analysis.py (1890 bytes)
    │   ├── test_node_models.py (4792 bytes)
    │   ├── test_ignore_patterns_manager.py (6931 bytes)
    │   └── test_input_handler.py (786 bytes)
    ├── __init__.py (274 bytes)
    ├── _codebase_digest.md (45444 bytes)
    ├── app.py (8653 bytes)
    ├── rich_output_formatter.py (5521 bytes)
    └── input_handler.py (1063 bytes)
```

## Summary

- Total files: 13
- Total directories: 2
- Total text file size (including ignored): 87.54 KB
- Total tokens: 18470
- Analyzed text content size: 87.54 KB

## File Contents

### core/models.py

```
from dataclasses import dataclass, field
from typing import List, Union
import tiktoken

@dataclass
class NodeAnalysis:
    name: str = ""
    is_ignored: bool = False

    @property
    def type(self) -> str:
        return NotImplemented
    
    @property
    def size(self) -> int:
        return NotImplemented
    
    def to_dict(self):
        return NotImplemented

@dataclass
class TextFileAnalysis(NodeAnalysis):
    file_content: str = ""

    @property
    def type(self) -> str:
        return "text_file"
    
    @property
    def size(self) -> int:
        return len(self.file_content)
    
    def count_tokens(self):
        """Counts the number of tokens in a text string."""
        enc = tiktoken.get_encoding("cl100k_base")
        try:
            return len(enc.encode(self.file_content, disallowed_special=()))
        except Exception as e:
            print(f"Warning: Error counting tokens: {str(e)}")
            return 0
        
    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "size": self.size,
            "is_ignored": self.is_ignored,
            "content": self.file_content
        }

@dataclass
class DirectoryAnalysis(NodeAnalysis):
    children: List[Union["DirectoryAnalysis", TextFileAnalysis]] = field(default_factory=list)

    @property
    def type(self) -> str:
        return "directory"

    def get_file_count(self) -> int:
        count = 0
        for child in self.children:
            if child.is_ignored:
                continue

            if isinstance(child, TextFileAnalysis):
                count += 1
            if isinstance(child, DirectoryAnalysis):
                count += child.get_file_count()
        return count
    
    def get_dir_count(self) -> int:
       count = 0
       for child in self.children:
           if child.is_ignored:
               continue 
           
           if isinstance(child, DirectoryAnalysis):
               count += 1 + child.get_dir_count()
       return count


    def get_total_tokens(self) -> int:
        tokens = 0
        for child in self.children:
            if child.is_ignored:
                continue

            if isinstance(child, TextFileAnalysis):
                tokens += child.count_tokens()
            elif isinstance(child, DirectoryAnalysis):
                tokens += child.get_total_tokens()
        return tokens

    @property
    def size(self) -> int:
        size = 0
        for child in self.children:
            if isinstance(child, TextFileAnalysis):
                 size += child.size
            elif isinstance(child, DirectoryAnalysis):
                 size += child.size

        return size

    def get_non_ignored_text_content_size(self) -> int:
        size = 0
        for child in self.children:
            if child.is_ignored:
                continue    

            if isinstance(child, TextFileAnalysis) and child.file_content:
                size += len(child.file_content)
            elif isinstance(child, DirectoryAnalysis):
               size += child.size
        return size
    
    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "size": self.size,
            "is_ignored": self.is_ignored,
            "non_ignored_text_content_size": self.get_non_ignored_text_content_size(),
            "total_tokens": self.get_total_tokens(),
            "file_count": self.get_file_count(),
            "dir_count": self.get_dir_count(),
            "children": [child.to_dict() for child in self.children]
        }
```

### core/codebase_analysis.py

```
import os

from core.ignore_patterns_manager import IgnorePatternManager
from core.models import DirectoryAnalysis, TextFileAnalysis

class CodebaseAnalysis:

    def is_text_file_old(self, file_path):
        """Determines if a file is likely a text file based on its content."""
        try:
            with open(file_path, 'rb') as file:
                chunk = file.read(1024)
            return not bool(chunk.translate(None, bytes([7, 8, 9, 10, 12, 13, 27] + list(range(0x20, 0x100)))))
        except IOError:
            return False

    def is_text_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                file.read()
            return True
        except UnicodeDecodeError:
            return False
        except FileNotFoundError:
            print("File not found.")
            return False

    def read_file_content(self, file_path):
        """Reads the content of a file, handling potential encoding errors."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def analyze_directory(self, path, ignore_patterns_manager: IgnorePatternManager, base_path, max_depth=None, current_depth=0) -> DirectoryAnalysis:
        """Recursively analyzes a directory and its contents."""
        if max_depth is not None and current_depth > max_depth:
            return None

        result = DirectoryAnalysis(name=os.path.basename(path))
        try:
            for item in os.listdir(path):                
                item_path = os.path.join(path, item)
                
                is_ignored = ignore_patterns_manager.should_ignore(item_path, base_path)
                print(f"Debug: Checking {item_path}, ignored: {is_ignored}")  # Debug line

                if os.path.isfile(item_path) and self.is_text_file(item_path):
                    file_size = os.path.getsize(item_path)

                if is_ignored:
                    continue  # Skip ignored items for further analysis

                if os.path.isfile(item_path):
                    file_size = os.path.getsize(item_path)
                    if self.is_text_file(item_path):
                        content = self.read_file_content(item_path)
                        print(f"Debug: Text file {item_path}, size: {file_size}, content size: {len(content)}")
                    else:
                        content = "[Non-text file]"
                        print(f"Debug: Non-text file {item_path}, size: {file_size}")

                    child = TextFileAnalysis(name=item, file_content=content, is_ignored=is_ignored)
                    result.children.append(child)
                elif os.path.isdir(item_path):
                    subdir = self.analyze_directory(item_path, ignore_patterns_manager, base_path, max_depth, current_depth + 1)
                    if subdir:
                        subdir.is_ignored = is_ignored
                        result.children.append(subdir)
                        
        except PermissionError:
            print(f"Permission denied: {path}")

        return result
```

### core/ignore_patterns_manager.py

```
import os
import fnmatch

class IgnorePatternManager:

    DEFAULT_IGNORE_PATTERNS = [
        '*.pyc', '*.pyo', '*.pyd', '__pycache__',  # Python
        'node_modules', 'bower_components',        # JavaScript
        '.git', '.svn', '.hg', '.gitignore',       # Version control
        'venv', '.venv', 'env',                    # Virtual environments
        '.idea', '.vscode',                        # IDEs
        '*.log', '*.bak', '*.swp', '*.tmp',        # Temporary and log files
        '.DS_Store',                               # macOS
        'Thumbs.db',                               # Windows
        'build', 'dist',                           # Build directories
        '*.egg-info',                              # Python egg info
        '*.so', '*.dylib', '*.dll'                 # Compiled libraries
    ]

    def __init__(self, 
                 base_path,
                 load_default_ignore_patterns=True, 
                 load_gitignore=True, 
                 load_cdigestignore=True,
                 extra_ignore_patterns=set()):
        self.base_path = base_path
        self.load_default_ignore_patterns=load_default_ignore_patterns
        self.load_gitignore=load_gitignore
        self.load_cdigestignore = load_cdigestignore
        self.extra_ignore_patterns = extra_ignore_patterns
        self.ignore_patterns = set()

        self.init_ignore_patterns()


    def init_ignore_patterns(self):
        patterns = set()

        if self.load_default_ignore_patterns:
            patterns.update(IgnorePatternManager.DEFAULT_IGNORE_PATTERNS)
        
        if self.extra_ignore_patterns:
            patterns.update(self.extra_ignore_patterns)
        
        cdigestignore_path = os.path.join(self.base_path, '.cdigestignore')
        if self.load_cdigestignore and os.path.exists(cdigestignore_path):
            with open(cdigestignore_path, 'r') as f:
                file_patterns = {line.strip() for line in f if line.strip() and not line.startswith('#')}
            patterns.update(file_patterns)
        
        gitignore_path = os.path.join(self.base_path, '.gitignore')
        if self.load_gitignore and os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                file_patterns = {line.strip() for line in f if line.strip() and not line.startswith('#')}
            patterns.update(file_patterns)

        self.ignore_patterns = patterns
    
    def should_ignore(self, path, base_path):
        """Checks if a file or directory should be ignored based on patterns."""
        name = os.path.basename(path)
        rel_path = os.path.relpath(path, base_path)
        abs_path = os.path.abspath(path)
        
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(name, pattern) or \
            fnmatch.fnmatch(rel_path, pattern) or \
            fnmatch.fnmatch(abs_path, pattern) or \
            (pattern.startswith('/') and fnmatch.fnmatch(abs_path, os.path.join(base_path, pattern[1:]))) or \
            any(fnmatch.fnmatch(part, pattern) for part in rel_path.split(os.sep)):
                return True
        return False
```

### output_formatter.py

```
from core.models import DirectoryAnalysis, NodeAnalysis, TextFileAnalysis
import os

class OutputFormatterBase:
    def output_file_extension(self):
        raise NotImplemented

    def format(self, data: DirectoryAnalysis) -> str:
        raise NotImplemented
    
    def generate_tree_string(self, node: NodeAnalysis, prefix="", is_last=True, show_size=False, show_ignored=False):
        """Generates a string representation of the directory tree."""
        if node.is_ignored and not show_ignored:
            return ""

        result = prefix + ("└── " if is_last else "├── ") + node.name

        if show_size and isinstance(node, TextFileAnalysis):
            result += f" ({node.size} bytes)"

        if node.is_ignored:
            result += " [IGNORED]"

        result += "\n"

        if isinstance(node, DirectoryAnalysis):
            prefix += "    " if is_last else "│   "
            children = node.children
            if not show_ignored:
                children = [child for child in children if not child.is_ignored]
            for i, child in enumerate(children):
                result += self.generate_tree_string(child, prefix, i == len(children) - 1, show_size, show_ignored)
        return result
    
    def generate_content_string(self, data: NodeAnalysis):
        """Generates a structured representation of file contents."""
        content = []

        def add_file_content(node, path=""):
            if isinstance(node, TextFileAnalysis) and not node.is_ignored and node.file_content != "[Non-text file]":
                content.append({
                    "path": os.path.join(path, node.name),
                    "content": node.file_content
                })
            elif isinstance(node, DirectoryAnalysis):
                for child in node.children:
                    add_file_content(child, os.path.join(path, node.name))

        add_file_content(data)
        return content
    
    def generate_summary_string(self, data: DirectoryAnalysis):
        summary = "\nSummary:\n"
        summary += f"Total files analyzed: {data.get_file_count()}\n"
        summary += f"Total directories analyzed: {data.get_dir_count()}\n"
        summary += f"Estimated output size: {data.size / 1024:.2f} KB\n"
        summary += f"Actual analyzed size: {data.get_non_ignored_text_content_size() / 1024:.2f} KB\n"
        summary += f"Total tokens: {data.get_total_tokens()}\n"
        summary += f"Actual text content size: {data.size / 1024:.2f} KB\n"
        
        return summary
    
class PlainTextOutputFormatter(OutputFormatterBase):
    def output_file_extension(self):
        return ".txt"
    
    def format(self, data: DirectoryAnalysis) -> str:
        output = f"Codebase Analysis for: {data.name}\n"
        output += "\nDirectory Structure:\n"
        output += self.generate_tree_string(data, show_size=True, show_ignored=True)
        output += self.generate_summary_string(data)
        output += "\nFile Contents:\n"
        for file in self.generate_content_string(data):
            output += f"\n{'=' * 50}\n"
            output += f"File: {file['path']}\n"
            output += f"{'=' * 50}\n"
            output += file['content']
            output += "\n"
        return output

class MarkdownOutputFormatter(OutputFormatterBase):
    def output_file_extension(self):
        return ".md"
    
    def format(self, data: DirectoryAnalysis) -> str:
        output = f"# Codebase Analysis for: {data.name}\n\n"
        output += "## Directory Structure\n\n"
        output += "```\n"
        output += self.generate_tree_string(data, show_size=True, show_ignored=True)
        output += "```\n\n"
        output += "## Summary\n\n"
        output += f"- Total files: {data.get_file_count()}\n"
        output += f"- Total directories: {data.get_dir_count()}\n"
        output += f"- Total text file size (including ignored): {data.size / 1024:.2f} KB\n"
        output += f"- Total tokens: {data.get_total_tokens()}\n"
        output += f"- Analyzed text content size: {data.get_non_ignored_text_content_size() / 1024:.2f} KB\n\n"
        output += "## File Contents\n\n"
        for file in self.generate_content_string(data):
            output += f"### {file['path']}\n\n```\n{file['content']}\n```\n\n"
        return output
```

### tests/test_codebase_analysis.py

```
import unittest
from unittest.mock import patch, mock_open
from core.codebase_analysis import CodebaseAnalysis
from core.models import DirectoryAnalysis, TextFileAnalysis
from core.ignore_patterns_manager import IgnorePatternManager

class TestCodebaseAnalysis(unittest.TestCase):

    @patch("core.codebase_analysis.os.listdir", return_value=["file1.txt", "file2.txt"])
    @patch('core.codebase_analysis.os.path.isfile', return_value=True)
    @patch('core.codebase_analysis.os.path.getsize', return_value=10)
    @patch("builtins.open", new_callable=mock_open, read_data="Loremm ipsum dolor sit amet")
    def test_analyze_directory_basic(self, mock_read, mock_file, mock_isfile, mock):
         ignore_manager = IgnorePatternManager(".", load_default_ignore_patterns=False)
         codebase_analysis = CodebaseAnalysis()
         result = codebase_analysis.analyze_directory(".", ignore_manager, ".", max_depth=10)
         self.assertEqual(len(result.children), 2)
         self.assertEqual(result.children[0].name, "file1.txt")
         self.assertEqual(result.children[1].name, "file2.txt")

    @patch("core.codebase_analysis.os.listdir", return_value=["file1.txt", "file2.py"])
    @patch('core.codebase_analysis.os.path.isfile', return_value=True)
    @patch('core.codebase_analysis.os.path.getsize', return_value=10)
    @patch("builtins.open", new_callable=mock_open, read_data="Loremm ipsum dolor sit amet")
    def test_analyze_directory_with_ignored(self, mock_read, mock_file, mock_isfile, mock):
         ignore_manager = IgnorePatternManager(".", load_default_ignore_patterns=False, extra_ignore_patterns=["*.py"])
         codebase_analysis = CodebaseAnalysis()
         result = codebase_analysis.analyze_directory(".", ignore_manager, ".", max_depth=10)
         self.assertEqual(len(result.children), 1)
         self.assertEqual(result.children[0].name, "file1.txt")
```

### tests/test_node_models.py

```
import unittest
from core.models import NodeAnalysis, DirectoryAnalysis, TextFileAnalysis

class TestNodeAnalysis(unittest.TestCase):
    
        def test_node_analysis(self):
            node = NodeAnalysis("test")
            self.assertEqual(node.name, "test")
    
        def test_directory_analysis(self):
            directory = DirectoryAnalysis("test")
            self.assertEqual(directory.name, "test")
            self.assertEqual(directory.type, "directory")
    
        def test_text_file_analysis(self):
            text_file = TextFileAnalysis("test")
            self.assertEqual(text_file.name, "test")
            self.assertEqual(text_file.type, "text_file")

        def test_empty_directory_analysis(self):
            directory = DirectoryAnalysis("test")
            self.assertEqual(directory.get_file_count(), 0)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_total_tokens(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 0)
            self.assertEqual(directory.size, 0)
        
        def test_directory_with_one_text_file(self):
            directory = DirectoryAnalysis("test")
            text_file = TextFileAnalysis("test")
            text_file.file_content = "length of this string is 27"

            directory.children.append(text_file)
            self.assertEqual(directory.get_file_count(), 1)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 27)
            self.assertEqual(directory.size, 27)

        def test_directory_with_ten_files(self):
            directory = DirectoryAnalysis("test")
            for i in range(10):
                text_file = TextFileAnalysis("test")
                text_file.file_content = "length of this string is 27"
                directory.children.append(text_file)
            self.assertEqual(directory.get_file_count(), 10)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 270)
            self.assertEqual(directory.size, 270)

        def test_directory_with_one_sub_directory(self):
            directory = DirectoryAnalysis("test")
            sub_directory = DirectoryAnalysis("test")
            text_file = TextFileAnalysis("test")
            text_file.file_content = "length of this string is 27"
            sub_directory.children.append(text_file)
            directory.children.append(sub_directory)
            self.assertEqual(directory.get_file_count(), 1)
            self.assertEqual(directory.get_dir_count(), 1)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 27)
            self.assertEqual(directory.size, 27)

        def test_directory_with_one_ignored_file(self):
            directory = DirectoryAnalysis("test")
            text_file = TextFileAnalysis("test")
            text_file.is_ignored = True
            text_file.file_content = "length of this string is 27"
            directory.children.append(text_file)
            self.assertEqual(directory.get_file_count(), 0)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 0)
            self.assertEqual(directory.size, 27)

        def test_directory_with_one_ignored_sub_directory(self):
            directory = DirectoryAnalysis("test")
            sub_directory = DirectoryAnalysis("test")
            sub_directory.is_ignored = True
            text_file = TextFileAnalysis("test")
            text_file.file_content = "length of this string is 27"
            sub_directory.children.append(text_file)
            directory.children.append(sub_directory)
            self.assertEqual(directory.get_file_count(), 0)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 0)
            self.assertEqual(directory.size, 27)

        def test_directory_with_one_ignored_file_and_one_text_file(self):
            directory = DirectoryAnalysis("test")
            text_file = TextFileAnalysis("test")
            text_file.is_ignored = True
            text_file.file_content = "length of this string is 27"
            directory.children.append(text_file)
            text_file = TextFileAnalysis("test")
            text_file.file_content = "length of this string is 27"
            directory.children.append(text_file)
            self.assertEqual(directory.get_file_count(), 1)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 27)
            self.assertEqual(directory.size, 54)
```

### tests/test_ignore_patterns_manager.py

```
import os
import unittest
from unittest.mock import patch, mock_open
from core.ignore_patterns_manager import IgnorePatternManager

class TestIgnorePatternsManager(unittest.TestCase):
        
        def test_ignore_patterns_manager_should_load_default_patterns(self):
            manager = IgnorePatternManager("./test", 
                                           load_default_ignore_patterns=True,
                                           load_gitignore=False,
                                           load_cdigestignore=False)
            self.assertSetEqual(manager.ignore_patterns, set(IgnorePatternManager.DEFAULT_IGNORE_PATTERNS))

        @patch('core.ignore_patterns_manager.os.path.exists', return_value=True)
        @patch("builtins.open", new_callable=mock_open, read_data=".java\n.class\n#comment\n")
        def test_load_cdigestignore(self, mock_file, mock_exists):
            manager = IgnorePatternManager("./test", 
                                           load_default_ignore_patterns=False,
                                           load_gitignore=False, 
                                           load_cdigestignore=True)
            
            mock_file.assert_called_once_with("./test/.cdigestignore", "r")
            self.assertSetEqual(manager.ignore_patterns, set([".java", ".class"]))

        @patch('core.ignore_patterns_manager.os.path.exists', return_value=True)
        def test_load_both_gitignore_and_cdigestignore(self, mock_exists):
            def mock_open_side_effect(path, mode="r"):
                if path.endswith(".cdigestignore"):
                    return mock_open(read_data=".java\n")()  # Mock for .cdigestignore
                elif path.endswith(".gitignore"):
                    return mock_open(read_data=".py\n")()  # Mock for .gitignore
                else:
                    raise FileNotFoundError(f"Unexpected file opened: {path}")  # Catch unexpected file opens

            with patch("builtins.open", new_callable=mock_open) as mock_file:
                mock_file.side_effect = mock_open_side_effect
                manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                                load_gitignore=True, load_cdigestignore=True)

            self.assertSetEqual(manager.ignore_patterns, {".java", ".py"})

        @patch('core.ignore_patterns_manager.os.path.exists', return_value=True)
        @patch("builtins.open", new_callable=mock_open, read_data=".java\n.class\n#comment\n")
        def test_load_gitignore(self, mock_file, mock_exists):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                            load_gitignore=True, load_cdigestignore=False)
            self.assertSetEqual(manager.ignore_patterns, set([".java", ".class"]))

        @patch('core.ignore_patterns_manager.os.path.exists', return_value=True)
        @patch("builtins.open", new_callable=mock_open, read_data=".java\n.class\n#comment\n")
        def test_load_gitignore_and_default(self, mock_file, mock_exists):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=True,
                                            load_gitignore=True, load_cdigestignore=False)
            
            expected_patterns = set(IgnorePatternManager.DEFAULT_IGNORE_PATTERNS)
            expected_patterns.update([".java", ".class"])

            self.assertSetEqual(manager.ignore_patterns, expected_patterns)
        
        def test_load_extra_patterns(self):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                        load_gitignore=False, load_cdigestignore=False,
                                        extra_ignore_patterns={"extra1", "extra2"})
            self.assertSetEqual(manager.ignore_patterns, {"extra1", "extra2"})

        def test_should_ignore_filename(self):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                        load_gitignore=False, load_cdigestignore=False,
                                        extra_ignore_patterns={"test.txt"})
            self.assertTrue(manager.should_ignore("./test/test.txt", "./test"))
            self.assertFalse(manager.should_ignore("./test/other.txt", "./test"))

        def test_should_ignore_relative_path(self):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                        load_gitignore=False, load_cdigestignore=False,
                                        extra_ignore_patterns={"sub/test.txt"})
            self.assertTrue(manager.should_ignore("./test/sub/test.txt", "./test"))
            self.assertFalse(manager.should_ignore("./test/sub/other.txt", "./test"))
            self.assertFalse(manager.should_ignore("./test/test.txt", "./test")) # Test that only the relative path is matched


        def test_should_ignore_absolute_path(self):
            base_path = os.path.abspath("./test")  # Get absolute path
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                            load_gitignore=False, load_cdigestignore=False,
                                            extra_ignore_patterns={os.path.join(base_path, "sub/test.txt")})
            
            self.assertTrue(manager.should_ignore(os.path.join(base_path, "sub/test.txt"), base_path))
            self.assertFalse(manager.should_ignore(os.path.join(base_path, "sub/other.txt"), base_path))


        def test_should_ignore_leading_slash_absolute_path(self):
            base_path = os.path.abspath("./test")  # Get absolute path
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                        load_gitignore=False, load_cdigestignore=False,
                                        extra_ignore_patterns={"/sub/test.txt"})
            self.assertTrue(manager.should_ignore(os.path.join(base_path, "sub/test.txt"), base_path))
            self.assertFalse(manager.should_ignore(os.path.join(base_path, "sub/other.txt"), base_path))
            self.assertFalse(manager.should_ignore(os.path.join(base_path, "test.txt"), base_path))

        def test_should_ignore_part_of_relative_path(self):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                        load_gitignore=False, load_cdigestignore=False,
                                        extra_ignore_patterns={"sub"}) # Ignores anything containing "sub" in the path
            self.assertTrue(manager.should_ignore("./test/sub/test.txt", "./test"))
            self.assertTrue(manager.should_ignore("./test/deeper/sub/test.txt", "./test"))
            self.assertFalse(manager.should_ignore("./test/other/test.txt", "./test"))
```

### tests/test_input_handler.py

```
import unittest
from unittest.mock import patch
from input_handler import InputHandler

class TestInputHandler(unittest.TestCase):

    def test_get_regular_input(self):
        handler = InputHandler(no_input=False)
        with patch('builtins.input', return_value='Yes'):
            self.assertEqual(handler.get_input('Enter something: '), 'yes')

    def test_surpassed_input_should_return_assigned_detault(self):
        handler = InputHandler(no_input=True, default_response='n')
        self.assertEqual(handler.get_input('Enter something: '), 'n')

    def test_surpassed_input_should_return_yes_by_default(self):
        handler = InputHandler(no_input=True)
        self.assertEqual(handler.get_input('Enter something: '), 'y')

if __name__ == '__main__':
    unittest.main()
```

### __init__.py

```
import os

def read_version():
    version_file = os.path.join(os.path.dirname(__file__), '..', 'VERSION')
    try:
        with open(version_file) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"

__version__ = read_version()
```

### _codebase_digest.md

```
# Codebase Analysis for: 

## Directory Structure

```
└── 
    ├── core
    │   ├── models.py (3617 bytes)
    │   ├── codebase_analysis.py (3214 bytes)
    │   └── ignore_patterns_manager.py (3144 bytes)
    ├── output_formatter.py (4307 bytes)
    ├── tests
    │   ├── test_codebase_analysis.py (1890 bytes)
    │   ├── test_node_models.py (4792 bytes)
    │   ├── test_ignore_patterns_manager.py (6931 bytes)
    │   └── test_input_handler.py (786 bytes)
    ├── __init__.py (274 bytes)
    ├── app.py (8653 bytes)
    ├── rich_output_formatter.py (5521 bytes)
    └── input_handler.py (1063 bytes)
```

## Summary

- Total files: 12
- Total directories: 2
- Total text file size (including ignored): 43.16 KB
- Total tokens: 9056
- Analyzed text content size: 43.16 KB

## File Contents

### core/models.py

```
from dataclasses import dataclass, field
from typing import List, Union
import tiktoken

@dataclass
class NodeAnalysis:
    name: str = ""
    is_ignored: bool = False

    @property
    def type(self) -> str:
        return NotImplemented
    
    @property
    def size(self) -> int:
        return NotImplemented
    
    def to_dict(self):
        return NotImplemented

@dataclass
class TextFileAnalysis(NodeAnalysis):
    file_content: str = ""

    @property
    def type(self) -> str:
        return "text_file"
    
    @property
    def size(self) -> int:
        return len(self.file_content)
    
    def count_tokens(self):
        """Counts the number of tokens in a text string."""
        enc = tiktoken.get_encoding("cl100k_base")
        try:
            return len(enc.encode(self.file_content, disallowed_special=()))
        except Exception as e:
            print(f"Warning: Error counting tokens: {str(e)}")
            return 0
        
    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "size": self.size,
            "is_ignored": self.is_ignored,
            "content": self.file_content
        }

@dataclass
class DirectoryAnalysis(NodeAnalysis):
    children: List[Union["DirectoryAnalysis", TextFileAnalysis]] = field(default_factory=list)

    @property
    def type(self) -> str:
        return "directory"

    def get_file_count(self) -> int:
        count = 0
        for child in self.children:
            if child.is_ignored:
                continue

            if isinstance(child, TextFileAnalysis):
                count += 1
            if isinstance(child, DirectoryAnalysis):
                count += child.get_file_count()
        return count
    
    def get_dir_count(self) -> int:
       count = 0
       for child in self.children:
           if child.is_ignored:
               continue 
           
           if isinstance(child, DirectoryAnalysis):
               count += 1 + child.get_dir_count()
       return count


    def get_total_tokens(self) -> int:
        tokens = 0
        for child in self.children:
            if child.is_ignored:
                continue

            if isinstance(child, TextFileAnalysis):
                tokens += child.count_tokens()
            elif isinstance(child, DirectoryAnalysis):
                tokens += child.get_total_tokens()
        return tokens

    @property
    def size(self) -> int:
        size = 0
        for child in self.children:
            if isinstance(child, TextFileAnalysis):
                 size += child.size
            elif isinstance(child, DirectoryAnalysis):
                 size += child.size

        return size

    def get_non_ignored_text_content_size(self) -> int:
        size = 0
        for child in self.children:
            if child.is_ignored:
                continue    

            if isinstance(child, TextFileAnalysis) and child.file_content:
                size += len(child.file_content)
            elif isinstance(child, DirectoryAnalysis):
               size += child.size
        return size
    
    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "size": self.size,
            "is_ignored": self.is_ignored,
            "non_ignored_text_content_size": self.get_non_ignored_text_content_size(),
            "total_tokens": self.get_total_tokens(),
            "file_count": self.get_file_count(),
            "dir_count": self.get_dir_count(),
            "children": [child.to_dict() for child in self.children]
        }
```

### core/codebase_analysis.py

```
import os

from core.ignore_patterns_manager import IgnorePatternManager
from core.models import DirectoryAnalysis, TextFileAnalysis

class CodebaseAnalysis:

    def is_text_file_old(self, file_path):
        """Determines if a file is likely a text file based on its content."""
        try:
            with open(file_path, 'rb') as file:
                chunk = file.read(1024)
            return not bool(chunk.translate(None, bytes([7, 8, 9, 10, 12, 13, 27] + list(range(0x20, 0x100)))))
        except IOError:
            return False

    def is_text_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                file.read()
            return True
        except UnicodeDecodeError:
            return False
        except FileNotFoundError:
            print("File not found.")
            return False

    def read_file_content(self, file_path):
        """Reads the content of a file, handling potential encoding errors."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def analyze_directory(self, path, ignore_patterns_manager: IgnorePatternManager, base_path, max_depth=None, current_depth=0) -> DirectoryAnalysis:
        """Recursively analyzes a directory and its contents."""
        if max_depth is not None and current_depth > max_depth:
            return None

        result = DirectoryAnalysis(name=os.path.basename(path))
        try:
            for item in os.listdir(path):                
                item_path = os.path.join(path, item)
                
                is_ignored = ignore_patterns_manager.should_ignore(item_path, base_path)
                print(f"Debug: Checking {item_path}, ignored: {is_ignored}")  # Debug line

                if os.path.isfile(item_path) and self.is_text_file(item_path):
                    file_size = os.path.getsize(item_path)

                if is_ignored:
                    continue  # Skip ignored items for further analysis

                if os.path.isfile(item_path):
                    file_size = os.path.getsize(item_path)
                    if self.is_text_file(item_path):
                        content = self.read_file_content(item_path)
                        print(f"Debug: Text file {item_path}, size: {file_size}, content size: {len(content)}")
                    else:
                        content = "[Non-text file]"
                        print(f"Debug: Non-text file {item_path}, size: {file_size}")

                    child = TextFileAnalysis(name=item, file_content=content, is_ignored=is_ignored)
                    result.children.append(child)
                elif os.path.isdir(item_path):
                    subdir = self.analyze_directory(item_path, ignore_patterns_manager, base_path, max_depth, current_depth + 1)
                    if subdir:
                        subdir.is_ignored = is_ignored
                        result.children.append(subdir)
                        
        except PermissionError:
            print(f"Permission denied: {path}")

        return result
```

### core/ignore_patterns_manager.py

```
import os
import fnmatch

class IgnorePatternManager:

    DEFAULT_IGNORE_PATTERNS = [
        '*.pyc', '*.pyo', '*.pyd', '__pycache__',  # Python
        'node_modules', 'bower_components',        # JavaScript
        '.git', '.svn', '.hg', '.gitignore',       # Version control
        'venv', '.venv', 'env',                    # Virtual environments
        '.idea', '.vscode',                        # IDEs
        '*.log', '*.bak', '*.swp', '*.tmp',        # Temporary and log files
        '.DS_Store',                               # macOS
        'Thumbs.db',                               # Windows
        'build', 'dist',                           # Build directories
        '*.egg-info',                              # Python egg info
        '*.so', '*.dylib', '*.dll'                 # Compiled libraries
    ]

    def __init__(self, 
                 base_path,
                 load_default_ignore_patterns=True, 
                 load_gitignore=True, 
                 load_cdigestignore=True,
                 extra_ignore_patterns=set()):
        self.base_path = base_path
        self.load_default_ignore_patterns=load_default_ignore_patterns
        self.load_gitignore=load_gitignore
        self.load_cdigestignore = load_cdigestignore
        self.extra_ignore_patterns = extra_ignore_patterns
        self.ignore_patterns = set()

        self.init_ignore_patterns()


    def init_ignore_patterns(self):
        patterns = set()

        if self.load_default_ignore_patterns:
            patterns.update(IgnorePatternManager.DEFAULT_IGNORE_PATTERNS)
        
        if self.extra_ignore_patterns:
            patterns.update(self.extra_ignore_patterns)
        
        cdigestignore_path = os.path.join(self.base_path, '.cdigestignore')
        if self.load_cdigestignore and os.path.exists(cdigestignore_path):
            with open(cdigestignore_path, 'r') as f:
                file_patterns = {line.strip() for line in f if line.strip() and not line.startswith('#')}
            patterns.update(file_patterns)
        
        gitignore_path = os.path.join(self.base_path, '.gitignore')
        if self.load_gitignore and os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                file_patterns = {line.strip() for line in f if line.strip() and not line.startswith('#')}
            patterns.update(file_patterns)

        self.ignore_patterns = patterns
    
    def should_ignore(self, path, base_path):
        """Checks if a file or directory should be ignored based on patterns."""
        name = os.path.basename(path)
        rel_path = os.path.relpath(path, base_path)
        abs_path = os.path.abspath(path)
        
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(name, pattern) or \
            fnmatch.fnmatch(rel_path, pattern) or \
            fnmatch.fnmatch(abs_path, pattern) or \
            (pattern.startswith('/') and fnmatch.fnmatch(abs_path, os.path.join(base_path, pattern[1:]))) or \
            any(fnmatch.fnmatch(part, pattern) for part in rel_path.split(os.sep)):
                return True
        return False
```

### output_formatter.py

```
from core.models import DirectoryAnalysis, NodeAnalysis, TextFileAnalysis
import os

class OutputFormatterBase:
    def output_file_extension(self):
        raise NotImplemented

    def format(self, data: DirectoryAnalysis) -> str:
        raise NotImplemented
    
    def generate_tree_string(self, node: NodeAnalysis, prefix="", is_last=True, show_size=False, show_ignored=False):
        """Generates a string representation of the directory tree."""
        if node.is_ignored and not show_ignored:
            return ""

        result = prefix + ("└── " if is_last else "├── ") + node.name

        if show_size and isinstance(node, TextFileAnalysis):
            result += f" ({node.size} bytes)"

        if node.is_ignored:
            result += " [IGNORED]"

        result += "\n"

        if isinstance(node, DirectoryAnalysis):
            prefix += "    " if is_last else "│   "
            children = node.children
            if not show_ignored:
                children = [child for child in children if not child.is_ignored]
            for i, child in enumerate(children):
                result += self.generate_tree_string(child, prefix, i == len(children) - 1, show_size, show_ignored)
        return result
    
    def generate_content_string(self, data: NodeAnalysis):
        """Generates a structured representation of file contents."""
        content = []

        def add_file_content(node, path=""):
            if isinstance(node, TextFileAnalysis) and not node.is_ignored and node.file_content != "[Non-text file]":
                content.append({
                    "path": os.path.join(path, node.name),
                    "content": node.file_content
                })
            elif isinstance(node, DirectoryAnalysis):
                for child in node.children:
                    add_file_content(child, os.path.join(path, node.name))

        add_file_content(data)
        return content
    
    def generate_summary_string(self, data: DirectoryAnalysis):
        summary = "\nSummary:\n"
        summary += f"Total files analyzed: {data.get_file_count()}\n"
        summary += f"Total directories analyzed: {data.get_dir_count()}\n"
        summary += f"Estimated output size: {data.size / 1024:.2f} KB\n"
        summary += f"Actual analyzed size: {data.get_non_ignored_text_content_size() / 1024:.2f} KB\n"
        summary += f"Total tokens: {data.get_total_tokens()}\n"
        summary += f"Actual text content size: {data.size / 1024:.2f} KB\n"
        
        return summary
    
class PlainTextOutputFormatter(OutputFormatterBase):
    def output_file_extension(self):
        return ".txt"
    
    def format(self, data: DirectoryAnalysis) -> str:
        output = f"Codebase Analysis for: {data.name}\n"
        output += "\nDirectory Structure:\n"
        output += self.generate_tree_string(data, show_size=True, show_ignored=True)
        output += self.generate_summary_string(data)
        output += "\nFile Contents:\n"
        for file in self.generate_content_string(data):
            output += f"\n{'=' * 50}\n"
            output += f"File: {file['path']}\n"
            output += f"{'=' * 50}\n"
            output += file['content']
            output += "\n"
        return output

class MarkdownOutputFormatter(OutputFormatterBase):
    def output_file_extension(self):
        return ".md"
    
    def format(self, data: DirectoryAnalysis) -> str:
        output = f"# Codebase Analysis for: {data.name}\n\n"
        output += "## Directory Structure\n\n"
        output += "```\n"
        output += self.generate_tree_string(data, show_size=True, show_ignored=True)
        output += "```\n\n"
        output += "## Summary\n\n"
        output += f"- Total files: {data.get_file_count()}\n"
        output += f"- Total directories: {data.get_dir_count()}\n"
        output += f"- Total text file size (including ignored): {data.size / 1024:.2f} KB\n"
        output += f"- Total tokens: {data.get_total_tokens()}\n"
        output += f"- Analyzed text content size: {data.get_non_ignored_text_content_size() / 1024:.2f} KB\n\n"
        output += "## File Contents\n\n"
        for file in self.generate_content_string(data):
            output += f"### {file['path']}\n\n```\n{file['content']}\n```\n\n"
        return output
```

### tests/test_codebase_analysis.py

```
import unittest
from unittest.mock import patch, mock_open
from core.codebase_analysis import CodebaseAnalysis
from core.models import DirectoryAnalysis, TextFileAnalysis
from core.ignore_patterns_manager import IgnorePatternManager

class TestCodebaseAnalysis(unittest.TestCase):

    @patch("core.codebase_analysis.os.listdir", return_value=["file1.txt", "file2.txt"])
    @patch('core.codebase_analysis.os.path.isfile', return_value=True)
    @patch('core.codebase_analysis.os.path.getsize', return_value=10)
    @patch("builtins.open", new_callable=mock_open, read_data="Loremm ipsum dolor sit amet")
    def test_analyze_directory_basic(self, mock_read, mock_file, mock_isfile, mock):
         ignore_manager = IgnorePatternManager(".", load_default_ignore_patterns=False)
         codebase_analysis = CodebaseAnalysis()
         result = codebase_analysis.analyze_directory(".", ignore_manager, ".", max_depth=10)
         self.assertEqual(len(result.children), 2)
         self.assertEqual(result.children[0].name, "file1.txt")
         self.assertEqual(result.children[1].name, "file2.txt")

    @patch("core.codebase_analysis.os.listdir", return_value=["file1.txt", "file2.py"])
    @patch('core.codebase_analysis.os.path.isfile', return_value=True)
    @patch('core.codebase_analysis.os.path.getsize', return_value=10)
    @patch("builtins.open", new_callable=mock_open, read_data="Loremm ipsum dolor sit amet")
    def test_analyze_directory_with_ignored(self, mock_read, mock_file, mock_isfile, mock):
         ignore_manager = IgnorePatternManager(".", load_default_ignore_patterns=False, extra_ignore_patterns=["*.py"])
         codebase_analysis = CodebaseAnalysis()
         result = codebase_analysis.analyze_directory(".", ignore_manager, ".", max_depth=10)
         self.assertEqual(len(result.children), 1)
         self.assertEqual(result.children[0].name, "file1.txt")
```

### tests/test_node_models.py

```
import unittest
from core.models import NodeAnalysis, DirectoryAnalysis, TextFileAnalysis

class TestNodeAnalysis(unittest.TestCase):
    
        def test_node_analysis(self):
            node = NodeAnalysis("test")
            self.assertEqual(node.name, "test")
    
        def test_directory_analysis(self):
            directory = DirectoryAnalysis("test")
            self.assertEqual(directory.name, "test")
            self.assertEqual(directory.type, "directory")
    
        def test_text_file_analysis(self):
            text_file = TextFileAnalysis("test")
            self.assertEqual(text_file.name, "test")
            self.assertEqual(text_file.type, "text_file")

        def test_empty_directory_analysis(self):
            directory = DirectoryAnalysis("test")
            self.assertEqual(directory.get_file_count(), 0)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_total_tokens(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 0)
            self.assertEqual(directory.size, 0)
        
        def test_directory_with_one_text_file(self):
            directory = DirectoryAnalysis("test")
            text_file = TextFileAnalysis("test")
            text_file.file_content = "length of this string is 27"

            directory.children.append(text_file)
            self.assertEqual(directory.get_file_count(), 1)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 27)
            self.assertEqual(directory.size, 27)

        def test_directory_with_ten_files(self):
            directory = DirectoryAnalysis("test")
            for i in range(10):
                text_file = TextFileAnalysis("test")
                text_file.file_content = "length of this string is 27"
                directory.children.append(text_file)
            self.assertEqual(directory.get_file_count(), 10)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 270)
            self.assertEqual(directory.size, 270)

        def test_directory_with_one_sub_directory(self):
            directory = DirectoryAnalysis("test")
            sub_directory = DirectoryAnalysis("test")
            text_file = TextFileAnalysis("test")
            text_file.file_content = "length of this string is 27"
            sub_directory.children.append(text_file)
            directory.children.append(sub_directory)
            self.assertEqual(directory.get_file_count(), 1)
            self.assertEqual(directory.get_dir_count(), 1)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 27)
            self.assertEqual(directory.size, 27)

        def test_directory_with_one_ignored_file(self):
            directory = DirectoryAnalysis("test")
            text_file = TextFileAnalysis("test")
            text_file.is_ignored = True
            text_file.file_content = "length of this string is 27"
            directory.children.append(text_file)
            self.assertEqual(directory.get_file_count(), 0)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 0)
            self.assertEqual(directory.size, 27)

        def test_directory_with_one_ignored_sub_directory(self):
            directory = DirectoryAnalysis("test")
            sub_directory = DirectoryAnalysis("test")
            sub_directory.is_ignored = True
            text_file = TextFileAnalysis("test")
            text_file.file_content = "length of this string is 27"
            sub_directory.children.append(text_file)
            directory.children.append(sub_directory)
            self.assertEqual(directory.get_file_count(), 0)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 0)
            self.assertEqual(directory.size, 27)

        def test_directory_with_one_ignored_file_and_one_text_file(self):
            directory = DirectoryAnalysis("test")
            text_file = TextFileAnalysis("test")
            text_file.is_ignored = True
            text_file.file_content = "length of this string is 27"
            directory.children.append(text_file)
            text_file = TextFileAnalysis("test")
            text_file.file_content = "length of this string is 27"
            directory.children.append(text_file)
            self.assertEqual(directory.get_file_count(), 1)
            self.assertEqual(directory.get_dir_count(), 0)
            self.assertEqual(directory.get_non_ignored_text_content_size(), 27)
            self.assertEqual(directory.size, 54)
```

### tests/test_ignore_patterns_manager.py

```
import os
import unittest
from unittest.mock import patch, mock_open
from core.ignore_patterns_manager import IgnorePatternManager

class TestIgnorePatternsManager(unittest.TestCase):
        
        def test_ignore_patterns_manager_should_load_default_patterns(self):
            manager = IgnorePatternManager("./test", 
                                           load_default_ignore_patterns=True,
                                           load_gitignore=False,
                                           load_cdigestignore=False)
            self.assertSetEqual(manager.ignore_patterns, set(IgnorePatternManager.DEFAULT_IGNORE_PATTERNS))

        @patch('core.ignore_patterns_manager.os.path.exists', return_value=True)
        @patch("builtins.open", new_callable=mock_open, read_data=".java\n.class\n#comment\n")
        def test_load_cdigestignore(self, mock_file, mock_exists):
            manager = IgnorePatternManager("./test", 
                                           load_default_ignore_patterns=False,
                                           load_gitignore=False, 
                                           load_cdigestignore=True)
            
            mock_file.assert_called_once_with("./test/.cdigestignore", "r")
            self.assertSetEqual(manager.ignore_patterns, set([".java", ".class"]))

        @patch('core.ignore_patterns_manager.os.path.exists', return_value=True)
        def test_load_both_gitignore_and_cdigestignore(self, mock_exists):
            def mock_open_side_effect(path, mode="r"):
                if path.endswith(".cdigestignore"):
                    return mock_open(read_data=".java\n")()  # Mock for .cdigestignore
                elif path.endswith(".gitignore"):
                    return mock_open(read_data=".py\n")()  # Mock for .gitignore
                else:
                    raise FileNotFoundError(f"Unexpected file opened: {path}")  # Catch unexpected file opens

            with patch("builtins.open", new_callable=mock_open) as mock_file:
                mock_file.side_effect = mock_open_side_effect
                manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                                load_gitignore=True, load_cdigestignore=True)

            self.assertSetEqual(manager.ignore_patterns, {".java", ".py"})

        @patch('core.ignore_patterns_manager.os.path.exists', return_value=True)
        @patch("builtins.open", new_callable=mock_open, read_data=".java\n.class\n#comment\n")
        def test_load_gitignore(self, mock_file, mock_exists):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                            load_gitignore=True, load_cdigestignore=False)
            self.assertSetEqual(manager.ignore_patterns, set([".java", ".class"]))

        @patch('core.ignore_patterns_manager.os.path.exists', return_value=True)
        @patch("builtins.open", new_callable=mock_open, read_data=".java\n.class\n#comment\n")
        def test_load_gitignore_and_default(self, mock_file, mock_exists):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=True,
                                            load_gitignore=True, load_cdigestignore=False)
            
            expected_patterns = set(IgnorePatternManager.DEFAULT_IGNORE_PATTERNS)
            expected_patterns.update([".java", ".class"])

            self.assertSetEqual(manager.ignore_patterns, expected_patterns)
        
        def test_load_extra_patterns(self):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                        load_gitignore=False, load_cdigestignore=False,
                                        extra_ignore_patterns={"extra1", "extra2"})
            self.assertSetEqual(manager.ignore_patterns, {"extra1", "extra2"})

        def test_should_ignore_filename(self):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                        load_gitignore=False, load_cdigestignore=False,
                                        extra_ignore_patterns={"test.txt"})
            self.assertTrue(manager.should_ignore("./test/test.txt", "./test"))
            self.assertFalse(manager.should_ignore("./test/other.txt", "./test"))

        def test_should_ignore_relative_path(self):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                        load_gitignore=False, load_cdigestignore=False,
                                        extra_ignore_patterns={"sub/test.txt"})
            self.assertTrue(manager.should_ignore("./test/sub/test.txt", "./test"))
            self.assertFalse(manager.should_ignore("./test/sub/other.txt", "./test"))
            self.assertFalse(manager.should_ignore("./test/test.txt", "./test")) # Test that only the relative path is matched


        def test_should_ignore_absolute_path(self):
            base_path = os.path.abspath("./test")  # Get absolute path
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                            load_gitignore=False, load_cdigestignore=False,
                                            extra_ignore_patterns={os.path.join(base_path, "sub/test.txt")})
            
            self.assertTrue(manager.should_ignore(os.path.join(base_path, "sub/test.txt"), base_path))
            self.assertFalse(manager.should_ignore(os.path.join(base_path, "sub/other.txt"), base_path))


        def test_should_ignore_leading_slash_absolute_path(self):
            base_path = os.path.abspath("./test")  # Get absolute path
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                        load_gitignore=False, load_cdigestignore=False,
                                        extra_ignore_patterns={"/sub/test.txt"})
            self.assertTrue(manager.should_ignore(os.path.join(base_path, "sub/test.txt"), base_path))
            self.assertFalse(manager.should_ignore(os.path.join(base_path, "sub/other.txt"), base_path))
            self.assertFalse(manager.should_ignore(os.path.join(base_path, "test.txt"), base_path))

        def test_should_ignore_part_of_relative_path(self):
            manager = IgnorePatternManager("./test", load_default_ignore_patterns=False,
                                        load_gitignore=False, load_cdigestignore=False,
                                        extra_ignore_patterns={"sub"}) # Ignores anything containing "sub" in the path
            self.assertTrue(manager.should_ignore("./test/sub/test.txt", "./test"))
            self.assertTrue(manager.should_ignore("./test/deeper/sub/test.txt", "./test"))
            self.assertFalse(manager.should_ignore("./test/other/test.txt", "./test"))
```

### tests/test_input_handler.py

```
import unittest
from unittest.mock import patch
from input_handler import InputHandler

class TestInputHandler(unittest.TestCase):

    def test_get_regular_input(self):
        handler = InputHandler(no_input=False)
        with patch('builtins.input', return_value='Yes'):
            self.assertEqual(handler.get_input('Enter something: '), 'yes')

    def test_surpassed_input_should_return_assigned_detault(self):
        handler = InputHandler(no_input=True, default_response='n')
        self.assertEqual(handler.get_input('Enter something: '), 'n')

    def test_surpassed_input_should_return_yes_by_default(self):
        handler = InputHandler(no_input=True)
        self.assertEqual(handler.get_input('Enter something: '), 'y')

if __name__ == '__main__':
    unittest.main()
```

### __init__.py

```
import os

def read_version():
    version_file = os.path.join(os.path.dirname(__file__), '..', 'VERSION')
    try:
        with open(version_file) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"

__version__ = read_version()
```

### app.py

```
 # CodeConsolidator - Consolidates and analyzes codebases for insights.

import os
import argparse
from colorama import init, Fore, Style
import sys
import pyperclip

from output_formatter import OutputFormatterBase, MarkdownOutputFormatter, PlainTextOutputFormatter
from rich_output_formatter import XmlOutputFormatter, HtmlOutputFormatter, JsonOutputFormatter, ColoredTextOutputFormatter
from input_handler import InputHandler
from core.ignore_patterns_manager import IgnorePatternManager
from core.codebase_analysis import CodebaseAnalysis

# Initialize colorama for colorful console output.
init()

def print_frame(text):
    """Prints a framed text box with colored borders."""
    width = max(len(line) for line in text.split('\n')) + 4
    print(Fore.CYAN + "+" + "-" * (width - 2) + "+")
    for line in text.split('\n'):
        print(Fore.CYAN + "| " + Fore.WHITE + line.ljust(width - 4) + Fore.CYAN + " |")
    print(Fore.CYAN + "+" + "-" * (width - 2) + "+" + Style.RESET_ALL)

def main():
    parser = argparse.ArgumentParser(
        description="Analyze and visualize codebase structure.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("path", nargs="?", 
                        help="Path to the directory to analyze")
    parser.add_argument("-d", "--max-depth", type=int, 
                        help="Maximum depth for directory traversal")
    parser.add_argument("-o", "--output-format", 
                        choices=["text", "json", "markdown", "xml", "html"],
                        default="text", 
                        help="Output format (default: text)")
    parser.add_argument("-f", "--file", 
                        help="Output file name (default: <directory_name>_codebase_digest.<format_extension>)")
    parser.add_argument("--show-size", action="store_true", 
                        help="Show file sizes in directory tree")
    parser.add_argument("--show-ignored", action="store_true", 
                        help="Show ignored files and directories in tree")
    parser.add_argument("--ignore", nargs="+", default=None,
                        help="Additional patterns to ignore. These will be added to the default ignore patterns.\n"
                             "Examples:\n"
                             "  --ignore '*.txt' 'temp_*' '/path/to/specific/file.py'\n"
                             "Patterns can use wildcards (* and ?) and can be:\n"
                             "  - Filenames (e.g., 'file.txt')\n"
                             "  - Directory names (e.g., 'node_modules')\n"
                             "  - File extensions (e.g., '*.pyc')\n"
                             "  - Paths (e.g., '/path/to/ignore')\n"
                             f"Default ignore patterns: {', '.join(IgnorePatternManager.DEFAULT_IGNORE_PATTERNS)}")
    parser.add_argument("--no-default-ignores", action="store_true",
                        help="Do not use default ignore patterns. Only use patterns specified by --ignore.")
    parser.add_argument("--no-content", action="store_true", 
                        help="Exclude file contents from the output")
    parser.add_argument("--max-size", type=int, default=10240, 
                        help="Maximum allowed text content size in KB (default: 10240 KB)")
    parser.add_argument("--copy-to-clipboard", action="store_true", 
                        help="Copy the output to clipboard after analysis")
    parser.add_argument("--no-input", action="store_true", help="Run the script without any user input")
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    if not args.path:
        print(Fore.RED + "Error: Path argument is required." + Style.RESET_ALL)
        parser.print_help(sys.stderr)
        sys.exit(1)

    input_handler = InputHandler(no_input=args.no_input)
    ignore_patterns_manager = IgnorePatternManager(args.path, 
                                                   load_default_ignore_patterns=not args.no_default_ignores, 
                                                   extra_ignore_patterns=set(args.ignore or []))
    codebase_analysis = CodebaseAnalysis()

    try:
        print(f"Debug: Ignore patterns after load_ignore_patterns: {ignore_patterns_manager.ignore_patterns}")

        print_frame("Codebase Digest")
        print(Fore.CYAN + "Analyzing directory: " + Fore.WHITE + args.path + Style.RESET_ALL)
        
        data = codebase_analysis.analyze_directory(args.path, ignore_patterns_manager, args.path, max_depth=args.max_depth)
        
        total_size = data.size
        estimated_output_size = data.get_non_ignored_text_content_size()
        estimated_output_size += data.get_file_count() * 100  # Assume 100 bytes per file for structure
        estimated_output_size += 1000  # Add 1KB for summary
        print(f"Estimated output size: {estimated_output_size / 1024:.2f} KB")

        if estimated_output_size / 1024 > args.max_size:
            print(Fore.YELLOW + f"\nWarning: The estimated output size ({estimated_output_size / 1024:.2f} KB) exceeds the maximum allowed size ({args.max_size} KB)." + Style.RESET_ALL)
            proceed = input_handler.get_input("Do you want to proceed? (y/n): ")
            if proceed != 'y':
                print(Fore.YELLOW + "Analysis aborted." + Style.RESET_ALL)
                sys.exit(0)
        elif total_size / 1024 > args.max_size * 2:  # Only show this if total size is significantly larger
            print(Fore.YELLOW + f"\nNote: The total size of all text files in the directory ({total_size / 1024:.2f} KB) is significantly larger than the estimated output size." + Style.RESET_ALL)
            print(Fore.YELLOW + "This is likely due to large files or directories that will be ignored in the analysis." + Style.RESET_ALL)

        output_formatter: OutputFormatterBase = None
        
        # Generate output based on the chosen format
        if args.output_format == "json":
            output_formatter = JsonOutputFormatter()
        elif args.output_format == "markdown":
            output_formatter = MarkdownOutputFormatter()
        elif args.output_format == "xml":
            output_formatter = XmlOutputFormatter()
        elif args.output_format == "html":
            output_formatter = HtmlOutputFormatter()
        else:
            output_formatter = PlainTextOutputFormatter()

        output = output_formatter.format(data)

        # Save the output to a file
        file_name = args.file or f"{os.path.basename(args.path)}_codebase_digest{output_formatter.output_file_extension()}"
        full_path = os.path.abspath(file_name)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(output)
        print(Fore.GREEN + f"\nAnalysis saved to: {full_path}" + Style.RESET_ALL)

        # Print colored summary to console immediately
        print_frame("Analysis Summary")
        colored_output_formatter = ColoredTextOutputFormatter()
        print(colored_output_formatter.generate_tree_string(data, show_size=args.show_size, show_ignored=args.show_ignored))
        print(colored_output_formatter.generate_summary_string(data))

        # Handle clipboard functionality for all formats
        if args.copy_to_clipboard:
            try:
                pyperclip.copy(output)
                print(Fore.GREEN + "Output copied to clipboard!" + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + f"Failed to copy to clipboard: {str(e)}" + Style.RESET_ALL)
        else:
            copy_to_clipboard = input_handler.get_input("Do you want to copy the output to clipboard? (y/n): ")
            if copy_to_clipboard == 'y':
                try:
                    pyperclip.copy(output)
                    print(Fore.GREEN + "Output copied to clipboard!" + Style.RESET_ALL)
                except Exception as e:
                    print(Fore.RED + f"Failed to copy to clipboard: {str(e)}" + Style.RESET_ALL)

    except Exception as e:
        print(Fore.RED + f"An error occurred: {str(e)}" + Style.RESET_ALL)
        sys.exit(1)

    if data.get_non_ignored_text_content_size() / 1024 > args.max_size:
        print(Fore.RED + f"\nWarning: The text content size ({data.get_non_ignored_text_content_size() / 1024:.2f} KB) exceeds the maximum allowed size ({args.max_size} KB)." + Style.RESET_ALL)
        proceed = input_handler.get_input("Do you want to proceed? (y/n): ")
        if proceed != 'y':
            print(Fore.YELLOW + "Analysis aborted." + Style.RESET_ALL)
            sys.exit(0)

if __name__ == "__main__":
    main()
```

### rich_output_formatter.py

```
from core.models import DirectoryAnalysis, NodeAnalysis, TextFileAnalysis
from colorama import init, Fore, Style
import xml.etree.ElementTree as ET
import html
import json
from output_formatter import OutputFormatterBase, PlainTextOutputFormatter

class ColoredTextOutputFormatter(PlainTextOutputFormatter):
    
    def generate_tree_string(self, node: NodeAnalysis, prefix="", is_last=True, show_size=False, show_ignored=False):
        """Generates a string representation of the directory tree."""
        if node.is_ignored and not show_ignored:
            return ""

        result = prefix + (Fore.GREEN + "└── " if is_last else "├── ")
        result += Fore.BLUE + node.name + Style.RESET_ALL

        if show_size and isinstance(node, TextFileAnalysis):
            size_str = f" ({node.size} bytes)"
            result += Fore.YELLOW + size_str + Style.RESET_ALL

        if node.is_ignored:
            ignored_str = " [IGNORED]"
            result += Fore.RED + ignored_str + Style.RESET_ALL

        result += "\n"

        if isinstance(node, DirectoryAnalysis):
            prefix += "    " if is_last else "│   "
            children = node.children
            if not show_ignored:
                children = [child for child in children if not child.is_ignored]
            for i, child in enumerate(children):
                result += self.generate_tree_string(child, prefix, i == len(children) - 1, show_size, show_ignored)
        return result
    
    def generate_content_string(self, data: NodeAnalysis):
        """Generates a structured representation of file contents."""
        content = []

        def add_file_content(node, path=""):
            if isinstance(node, TextFileAnalysis) and not node.is_ignored and node.file_content != "[Non-text file]":
                content.append({
                    "path": os.path.join(path, node.name),
                    "content": node.file_content
                })
            elif isinstance(node, DirectoryAnalysis):
                for child in node.children:
                    add_file_content(child, os.path.join(path, node.name))

        add_file_content(data)
        return content
    
    def generate_summary_string(self, data: DirectoryAnalysis):
        summary = "\nSummary:\n"
        summary += f"Total files analyzed: {data.get_file_count()}\n"
        summary += f"Total directories analyzed: {data.get_dir_count()}\n"
        summary += f"Total text file size (including ignored): {data.size / 1024:.2f} KB\n"
        summary += f"Analyzed text content size: {data.get_non_ignored_text_content_size() / 1024:.2f} KB\n"
        summary += f"Total tokens: {data.get_total_tokens()}\n"
        
        return Fore.CYAN + summary + Style.RESET_ALL

class JsonOutputFormatter(OutputFormatterBase):
    def output_file_extension(self):
        return ".json"
    
    def format(self, data: DirectoryAnalysis) -> str:
        return json.dumps(data.to_dict(), indent=2)

class XmlOutputFormatter(OutputFormatterBase):
    def output_file_extension(self):
        return ".xml"
    
    def format(self, data):
        root = ET.Element("codebase-analysis")
        ET.SubElement(root, "name").text = data.name
        structure = ET.SubElement(root, "directory-structure")
        structure.text = self.generate_tree_string(data, show_size=True, show_ignored=True)
        summary = ET.SubElement(root, "summary")
        ET.SubElement(summary, "total-files").text = str(data.get_file_count())
        ET.SubElement(summary, "total-directories").text = str(data.get_dir_count())
        ET.SubElement(summary, "total-text-file-size-kb").text = f"{data.size / 1024:.2f}"
        ET.SubElement(summary, "total-tokens").text = str(data.get_total_tokens())
        ET.SubElement(summary, "analyzed-text-content-size-kb").text = f"{data.get_non_ignored_text_content_size() / 1024:.2f}"
        contents = ET.SubElement(root, "file-contents")
        for file in self.generate_content_string(data):
            file_elem = ET.SubElement(contents, "file")
            ET.SubElement(file_elem, "path").text = file['path']
            ET.SubElement(file_elem, "content").text = file['content']
        return ET.tostring(root, encoding="unicode")
    
class HtmlOutputFormatter(OutputFormatterBase):
    def output_file_extension(self):
        return ".html"

    def format(self, data):
        output = f"""
        <html>
        <head>
            <title>Codebase Analysis for: {html.escape(data.name)}</title>
            <style>
                pre {{ white-space: pre-wrap; word-wrap: break-word; }}
            </style>
        </head>
        <body>
        <h1>Codebase Analysis for: {html.escape(data.name)}</h1>
        <h2>Directory Structure</h2>
        <pre>{html.escape(self.generate_tree_string(data, show_size=True, show_ignored=True))}</pre>
        <h2>Summary</h2>
        <ul>
        <li>Total files: {data.get_file_count()}</li>
        <li>Total directories: {data.get_dir_count()}</li>
        <li>Total text file size (including ignored): {data.size / 1024:.2f} KB</li>
        <li>Total tokens: {data.get_total_tokens()}</li>
        <li>Analyzed text content size: {data.get_non_ignored_text_content_size() / 1024:.2f} KB</li>
        </ul>
        <h2>File Contents</h2>
        """
        for file in self.generate_content_string(data):
            output += f"<h3>{html.escape(file['path'])}</h3><pre>{html.escape(file['content'])}</pre>"
        output += "</body></html>"
        return output
```

### input_handler.py

```
class InputHandler:
    """
    InputHandler class to manage user input with optional default responses.

    Attributes:
        no_input (bool): Flag to determine if user input should be bypassed.
        default_response (str): Default response to use when no_input is True.

    Methods:
        __init__(no_input=False, default_response='y'):
            Initializes the InputHandler with optional no_input flag and default response.
        
        get_input(prompt):
            Prompts the user for input unless no_input is True, in which case it returns the default response.
            Args:
                prompt (str): The prompt message to display to the user.
            Returns:
                str: The user's input or the default response.
    """
    def __init__(self, no_input=False, default_response='y'):
        self.no_input = no_input
        self.default_response = default_response

    def get_input(self, prompt):
        if not self.no_input:
            return input(prompt).lower().strip()
        return self.default_response

```


```

### app.py

```
 # CodeConsolidator - Consolidates and analyzes codebases for insights.

import os
import argparse
from colorama import init, Fore, Style
import sys
import pyperclip

from output_formatter import OutputFormatterBase, MarkdownOutputFormatter, PlainTextOutputFormatter
from rich_output_formatter import XmlOutputFormatter, HtmlOutputFormatter, JsonOutputFormatter, ColoredTextOutputFormatter
from input_handler import InputHandler
from core.ignore_patterns_manager import IgnorePatternManager
from core.codebase_analysis import CodebaseAnalysis

# Initialize colorama for colorful console output.
init()

def print_frame(text):
    """Prints a framed text box with colored borders."""
    width = max(len(line) for line in text.split('\n')) + 4
    print(Fore.CYAN + "+" + "-" * (width - 2) + "+")
    for line in text.split('\n'):
        print(Fore.CYAN + "| " + Fore.WHITE + line.ljust(width - 4) + Fore.CYAN + " |")
    print(Fore.CYAN + "+" + "-" * (width - 2) + "+" + Style.RESET_ALL)

def main():
    parser = argparse.ArgumentParser(
        description="Analyze and visualize codebase structure.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("path", nargs="?", 
                        help="Path to the directory to analyze")
    parser.add_argument("-d", "--max-depth", type=int, 
                        help="Maximum depth for directory traversal")
    parser.add_argument("-o", "--output-format", 
                        choices=["text", "json", "markdown", "xml", "html"],
                        default="text", 
                        help="Output format (default: text)")
    parser.add_argument("-f", "--file", 
                        help="Output file name (default: <directory_name>_codebase_digest.<format_extension>)")
    parser.add_argument("--show-size", action="store_true", 
                        help="Show file sizes in directory tree")
    parser.add_argument("--show-ignored", action="store_true", 
                        help="Show ignored files and directories in tree")
    parser.add_argument("--ignore", nargs="+", default=None,
                        help="Additional patterns to ignore. These will be added to the default ignore patterns.\n"
                             "Examples:\n"
                             "  --ignore '*.txt' 'temp_*' '/path/to/specific/file.py'\n"
                             "Patterns can use wildcards (* and ?) and can be:\n"
                             "  - Filenames (e.g., 'file.txt')\n"
                             "  - Directory names (e.g., 'node_modules')\n"
                             "  - File extensions (e.g., '*.pyc')\n"
                             "  - Paths (e.g., '/path/to/ignore')\n"
                             f"Default ignore patterns: {', '.join(IgnorePatternManager.DEFAULT_IGNORE_PATTERNS)}")
    parser.add_argument("--no-default-ignores", action="store_true",
                        help="Do not use default ignore patterns. Only use patterns specified by --ignore.")
    parser.add_argument("--no-content", action="store_true", 
                        help="Exclude file contents from the output")
    parser.add_argument("--max-size", type=int, default=10240, 
                        help="Maximum allowed text content size in KB (default: 10240 KB)")
    parser.add_argument("--copy-to-clipboard", action="store_true", 
                        help="Copy the output to clipboard after analysis")
    parser.add_argument("--no-input", action="store_true", help="Run the script without any user input")
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    if not args.path:
        print(Fore.RED + "Error: Path argument is required." + Style.RESET_ALL)
        parser.print_help(sys.stderr)
        sys.exit(1)

    input_handler = InputHandler(no_input=args.no_input)
    ignore_patterns_manager = IgnorePatternManager(args.path, 
                                                   load_default_ignore_patterns=not args.no_default_ignores, 
                                                   extra_ignore_patterns=set(args.ignore or []))
    codebase_analysis = CodebaseAnalysis()

    try:
        print(f"Debug: Ignore patterns after load_ignore_patterns: {ignore_patterns_manager.ignore_patterns}")

        print_frame("Codebase Digest")
        print(Fore.CYAN + "Analyzing directory: " + Fore.WHITE + args.path + Style.RESET_ALL)
        
        data = codebase_analysis.analyze_directory(args.path, ignore_patterns_manager, args.path, max_depth=args.max_depth)
        
        total_size = data.size
        estimated_output_size = data.get_non_ignored_text_content_size()
        estimated_output_size += data.get_file_count() * 100  # Assume 100 bytes per file for structure
        estimated_output_size += 1000  # Add 1KB for summary
        print(f"Estimated output size: {estimated_output_size / 1024:.2f} KB")

        if estimated_output_size / 1024 > args.max_size:
            print(Fore.YELLOW + f"\nWarning: The estimated output size ({estimated_output_size / 1024:.2f} KB) exceeds the maximum allowed size ({args.max_size} KB)." + Style.RESET_ALL)
            proceed = input_handler.get_input("Do you want to proceed? (y/n): ")
            if proceed != 'y':
                print(Fore.YELLOW + "Analysis aborted." + Style.RESET_ALL)
                sys.exit(0)
        elif total_size / 1024 > args.max_size * 2:  # Only show this if total size is significantly larger
            print(Fore.YELLOW + f"\nNote: The total size of all text files in the directory ({total_size / 1024:.2f} KB) is significantly larger than the estimated output size." + Style.RESET_ALL)
            print(Fore.YELLOW + "This is likely due to large files or directories that will be ignored in the analysis." + Style.RESET_ALL)

        output_formatter: OutputFormatterBase = None
        
        # Generate output based on the chosen format
        if args.output_format == "json":
            output_formatter = JsonOutputFormatter()
        elif args.output_format == "markdown":
            output_formatter = MarkdownOutputFormatter()
        elif args.output_format == "xml":
            output_formatter = XmlOutputFormatter()
        elif args.output_format == "html":
            output_formatter = HtmlOutputFormatter()
        else:
            output_formatter = PlainTextOutputFormatter()

        output = output_formatter.format(data)

        # Save the output to a file
        file_name = args.file or f"{os.path.basename(args.path)}_codebase_digest{output_formatter.output_file_extension()}"
        full_path = os.path.abspath(file_name)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(output)
        print(Fore.GREEN + f"\nAnalysis saved to: {full_path}" + Style.RESET_ALL)

        # Print colored summary to console immediately
        print_frame("Analysis Summary")
        colored_output_formatter = ColoredTextOutputFormatter()
        print(colored_output_formatter.generate_tree_string(data, show_size=args.show_size, show_ignored=args.show_ignored))
        print(colored_output_formatter.generate_summary_string(data))

        # Handle clipboard functionality for all formats
        if args.copy_to_clipboard:
            try:
                pyperclip.copy(output)
                print(Fore.GREEN + "Output copied to clipboard!" + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + f"Failed to copy to clipboard: {str(e)}" + Style.RESET_ALL)
        else:
            copy_to_clipboard = input_handler.get_input("Do you want to copy the output to clipboard? (y/n): ")
            if copy_to_clipboard == 'y':
                try:
                    pyperclip.copy(output)
                    print(Fore.GREEN + "Output copied to clipboard!" + Style.RESET_ALL)
                except Exception as e:
                    print(Fore.RED + f"Failed to copy to clipboard: {str(e)}" + Style.RESET_ALL)

    except Exception as e:
        print(Fore.RED + f"An error occurred: {str(e)}" + Style.RESET_ALL)
        sys.exit(1)

    if data.get_non_ignored_text_content_size() / 1024 > args.max_size:
        print(Fore.RED + f"\nWarning: The text content size ({data.get_non_ignored_text_content_size() / 1024:.2f} KB) exceeds the maximum allowed size ({args.max_size} KB)." + Style.RESET_ALL)
        proceed = input_handler.get_input("Do you want to proceed? (y/n): ")
        if proceed != 'y':
            print(Fore.YELLOW + "Analysis aborted." + Style.RESET_ALL)
            sys.exit(0)

if __name__ == "__main__":
    main()
```

### rich_output_formatter.py

```
from core.models import DirectoryAnalysis, NodeAnalysis, TextFileAnalysis
from colorama import init, Fore, Style
import xml.etree.ElementTree as ET
import html
import json
from output_formatter import OutputFormatterBase, PlainTextOutputFormatter

class ColoredTextOutputFormatter(PlainTextOutputFormatter):
    
    def generate_tree_string(self, node: NodeAnalysis, prefix="", is_last=True, show_size=False, show_ignored=False):
        """Generates a string representation of the directory tree."""
        if node.is_ignored and not show_ignored:
            return ""

        result = prefix + (Fore.GREEN + "└── " if is_last else "├── ")
        result += Fore.BLUE + node.name + Style.RESET_ALL

        if show_size and isinstance(node, TextFileAnalysis):
            size_str = f" ({node.size} bytes)"
            result += Fore.YELLOW + size_str + Style.RESET_ALL

        if node.is_ignored:
            ignored_str = " [IGNORED]"
            result += Fore.RED + ignored_str + Style.RESET_ALL

        result += "\n"

        if isinstance(node, DirectoryAnalysis):
            prefix += "    " if is_last else "│   "
            children = node.children
            if not show_ignored:
                children = [child for child in children if not child.is_ignored]
            for i, child in enumerate(children):
                result += self.generate_tree_string(child, prefix, i == len(children) - 1, show_size, show_ignored)
        return result
    
    def generate_content_string(self, data: NodeAnalysis):
        """Generates a structured representation of file contents."""
        content = []

        def add_file_content(node, path=""):
            if isinstance(node, TextFileAnalysis) and not node.is_ignored and node.file_content != "[Non-text file]":
                content.append({
                    "path": os.path.join(path, node.name),
                    "content": node.file_content
                })
            elif isinstance(node, DirectoryAnalysis):
                for child in node.children:
                    add_file_content(child, os.path.join(path, node.name))

        add_file_content(data)
        return content
    
    def generate_summary_string(self, data: DirectoryAnalysis):
        summary = "\nSummary:\n"
        summary += f"Total files analyzed: {data.get_file_count()}\n"
        summary += f"Total directories analyzed: {data.get_dir_count()}\n"
        summary += f"Total text file size (including ignored): {data.size / 1024:.2f} KB\n"
        summary += f"Analyzed text content size: {data.get_non_ignored_text_content_size() / 1024:.2f} KB\n"
        summary += f"Total tokens: {data.get_total_tokens()}\n"
        
        return Fore.CYAN + summary + Style.RESET_ALL

class JsonOutputFormatter(OutputFormatterBase):
    def output_file_extension(self):
        return ".json"
    
    def format(self, data: DirectoryAnalysis) -> str:
        return json.dumps(data.to_dict(), indent=2)

class XmlOutputFormatter(OutputFormatterBase):
    def output_file_extension(self):
        return ".xml"
    
    def format(self, data):
        root = ET.Element("codebase-analysis")
        ET.SubElement(root, "name").text = data.name
        structure = ET.SubElement(root, "directory-structure")
        structure.text = self.generate_tree_string(data, show_size=True, show_ignored=True)
        summary = ET.SubElement(root, "summary")
        ET.SubElement(summary, "total-files").text = str(data.get_file_count())
        ET.SubElement(summary, "total-directories").text = str(data.get_dir_count())
        ET.SubElement(summary, "total-text-file-size-kb").text = f"{data.size / 1024:.2f}"
        ET.SubElement(summary, "total-tokens").text = str(data.get_total_tokens())
        ET.SubElement(summary, "analyzed-text-content-size-kb").text = f"{data.get_non_ignored_text_content_size() / 1024:.2f}"
        contents = ET.SubElement(root, "file-contents")
        for file in self.generate_content_string(data):
            file_elem = ET.SubElement(contents, "file")
            ET.SubElement(file_elem, "path").text = file['path']
            ET.SubElement(file_elem, "content").text = file['content']
        return ET.tostring(root, encoding="unicode")
    
class HtmlOutputFormatter(OutputFormatterBase):
    def output_file_extension(self):
        return ".html"

    def format(self, data):
        output = f"""
        <html>
        <head>
            <title>Codebase Analysis for: {html.escape(data.name)}</title>
            <style>
                pre {{ white-space: pre-wrap; word-wrap: break-word; }}
            </style>
        </head>
        <body>
        <h1>Codebase Analysis for: {html.escape(data.name)}</h1>
        <h2>Directory Structure</h2>
        <pre>{html.escape(self.generate_tree_string(data, show_size=True, show_ignored=True))}</pre>
        <h2>Summary</h2>
        <ul>
        <li>Total files: {data.get_file_count()}</li>
        <li>Total directories: {data.get_dir_count()}</li>
        <li>Total text file size (including ignored): {data.size / 1024:.2f} KB</li>
        <li>Total tokens: {data.get_total_tokens()}</li>
        <li>Analyzed text content size: {data.get_non_ignored_text_content_size() / 1024:.2f} KB</li>
        </ul>
        <h2>File Contents</h2>
        """
        for file in self.generate_content_string(data):
            output += f"<h3>{html.escape(file['path'])}</h3><pre>{html.escape(file['content'])}</pre>"
        output += "</body></html>"
        return output
```

### input_handler.py

```
class InputHandler:
    """
    InputHandler class to manage user input with optional default responses.

    Attributes:
        no_input (bool): Flag to determine if user input should be bypassed.
        default_response (str): Default response to use when no_input is True.

    Methods:
        __init__(no_input=False, default_response='y'):
            Initializes the InputHandler with optional no_input flag and default response.
        
        get_input(prompt):
            Prompts the user for input unless no_input is True, in which case it returns the default response.
            Args:
                prompt (str): The prompt message to display to the user.
            Returns:
                str: The user's input or the default response.
    """
    def __init__(self, no_input=False, default_response='y'):
        self.no_input = no_input
        self.default_response = default_response

    def get_input(self, prompt):
        if not self.no_input:
            return input(prompt).lower().strip()
        return self.default_response

```

