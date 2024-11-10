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