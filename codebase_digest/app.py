 # CodeConsolidator - Consolidates and analyzes codebases for insights.

import os
import argparse
import fnmatch
from colorama import init, Fore, Style
import sys
import pyperclip

from output_formatter import OutputFormatterBase, MarkdownOutputFormatter, PlainTextOutputFormatter
from rich_output_formatter import XmlOutputFormatter, HtmlOutputFormatter, JsonOutputFormatter, ColoredTextOutputFormatter
from input_handler import InputHandler
from models import NodeAnalysis, TextFileAnalysis, DirectoryAnalysis

# Initialize colorama for colorful console output.
init()

# At the top of the file, after imports
DEFAULT_IGNORE_PATTERNS = [
    '*.pyc', '*.pyo', '*.pyd', '__pycache__',  # Python
    'node_modules', 'bower_components',        # JavaScript
    '.git', '.svn', '.hg', '.gitignore',                    # Version control
    'venv', '.venv', 'env',                    # Virtual environments
    '.idea', '.vscode',                        # IDEs
    '*.log', '*.bak', '*.swp', '*.tmp',        # Temporary and log files
    '.DS_Store',                               # macOS
    'Thumbs.db',                               # Windows
    'build', 'dist',                           # Build directories
    '*.egg-info',                              # Python egg info
    '*.so', '*.dylib', '*.dll'                 # Compiled libraries
]

def print_frame(text):
    """Prints a framed text box with colored borders."""
    width = max(len(line) for line in text.split('\n')) + 4
    print(Fore.CYAN + "+" + "-" * (width - 2) + "+")
    for line in text.split('\n'):
        print(Fore.CYAN + "| " + Fore.WHITE + line.ljust(width - 4) + Fore.CYAN + " |")
    print(Fore.CYAN + "+" + "-" * (width - 2) + "+" + Style.RESET_ALL)

def load_gitignore(path):
    """Loads .gitignore patterns from a given path."""
    gitignore_patterns = []
    gitignore_path = os.path.join(path, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            gitignore_patterns = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return gitignore_patterns

def should_ignore(path, base_path, ignore_patterns):
    """Checks if a file or directory should be ignored based on patterns."""
    name = os.path.basename(path)
    rel_path = os.path.relpath(path, base_path)
    abs_path = os.path.abspath(path)
    
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(name, pattern) or \
           fnmatch.fnmatch(rel_path, pattern) or \
           fnmatch.fnmatch(abs_path, pattern) or \
           (pattern.startswith('/') and fnmatch.fnmatch(abs_path, os.path.join(base_path, pattern[1:]))) or \
           any(fnmatch.fnmatch(part, pattern) for part in rel_path.split(os.sep)):
            print(f"Debug: Ignoring {path} due to pattern {pattern}")
            return True
    return False

def is_text_file(file_path):
    """Determines if a file is likely a text file based on its content."""
    try:
        with open(file_path, 'rb') as file:
            chunk = file.read(1024)
        return not bool(chunk.translate(None, bytes([7, 8, 9, 10, 12, 13, 27] + list(range(0x20, 0x100)))))
    except IOError:
        return False

def read_file_content(file_path):
    """Reads the content of a file, handling potential encoding errors."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def analyze_directory(path, ignore_patterns, base_path, include_git=False, max_depth=None, current_depth=0) -> DirectoryAnalysis:
    """Recursively analyzes a directory and its contents."""
    if max_depth is not None and current_depth > max_depth:
        return None

    result = DirectoryAnalysis(name=os.path.basename(path))

    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            
            # Skip .git directory unless explicitly included
            if item == '.git' and not include_git:
                continue

            is_ignored = should_ignore(item_path, base_path, ignore_patterns)
            print(f"Debug: Checking {item_path}, ignored: {is_ignored}")  # Debug line

            if os.path.isfile(item_path) and is_text_file(item_path):
                file_size = os.path.getsize(item_path)

            if is_ignored:
                continue  # Skip ignored items for further analysis

            # Log progress
            print(Fore.YELLOW + f"Analyzing: {item_path}" + Style.RESET_ALL)

            if os.path.isfile(item_path):
                file_size = os.path.getsize(item_path)
                is_text = is_text_file(item_path)
                if is_text:
                    content = read_file_content(item_path)
                    print(f"Debug: Text file {item_path}, size: {file_size}, content size: {len(content)}")
                else:
                    content = "[Non-text file]"
                    print(f"Debug: Non-text file {item_path}, size: {file_size}")
                child = TextFileAnalysis(name=item,
                                         file_content=content, 
                                         is_ignored=is_ignored)
                result.children.append(child)
            elif os.path.isdir(item_path):
                subdir = analyze_directory(item_path, ignore_patterns, base_path, include_git, max_depth, current_depth + 1)
                if subdir:
                    subdir.is_ignored = is_ignored
                    result.children.append(subdir)
                    
    except PermissionError:
        print(Fore.RED + f"Permission denied: {path}" + Style.RESET_ALL)

    return result

def load_ignore_patterns(args, base_path):
    patterns = set()
    if not args.no_default_ignores:
        patterns.update(DEFAULT_IGNORE_PATTERNS)
    
    if args.ignore:
        patterns.update(args.ignore)
    
    # Load patterns from .cdigestignore file if it exists
    cdigestignore_path = os.path.join(base_path, '.cdigestignore')
    if os.path.exists(cdigestignore_path):
        with open(cdigestignore_path, 'r') as f:
            file_patterns = {line.strip() for line in f if line.strip() and not line.startswith('#')}
        patterns.update(file_patterns)
    
    print(f"Debug: Final ignore patterns: {patterns}")
    return patterns

def estimate_output_size(path, ignore_patterns, base_path):
    estimated_size = 0
    file_count = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), base_path, ignore_patterns)]
        for file in files:
            file_path = os.path.join(root, file)
            if not should_ignore(file_path, base_path, ignore_patterns) and is_text_file(file_path):
                file_size = os.path.getsize(file_path)
                estimated_size += file_size
                file_count += 1
    
    # Add some overhead for the directory structure and summary
    estimated_size += file_count * 100  # Assume 100 bytes per file for structure
    estimated_size += 1000  # Add 1KB for summary

    return estimated_size

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
                             f"Default ignore patterns: {', '.join(DEFAULT_IGNORE_PATTERNS)}")
    parser.add_argument("--no-default-ignores", action="store_true",
                        help="Do not use default ignore patterns. Only use patterns specified by --ignore.")
    parser.add_argument("--no-content", action="store_true", 
                        help="Exclude file contents from the output")
    parser.add_argument("--include-git", action="store_true", 
                        help="Include .git directory in the analysis (ignored by default)")
    parser.add_argument("--max-size", type=int, default=10240, 
                        help="Maximum allowed text content size in KB (default: 10240 KB)")
    parser.add_argument("--copy-to-clipboard", action="store_true", 
                        help="Copy the output to clipboard after analysis")
    parser.add_argument("--no-input", action="store_true", help="Run the script without any user input")
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    input_handler = InputHandler(no_input=args.no_input)

    if not args.path:
        print(Fore.RED + "Error: Path argument is required." + Style.RESET_ALL)
        parser.print_help(sys.stderr)
        sys.exit(1)

    ignore_patterns = load_ignore_patterns(args, args.path)
    print(f"Debug: Ignore patterns after load_ignore_patterns: {ignore_patterns}")

    print_frame("Codebase Digest")
    print(Fore.CYAN + "Analyzing directory: " + Fore.WHITE + args.path + Style.RESET_ALL)

    # Estimate the output size
    estimated_size = estimate_output_size(args.path, ignore_patterns, args.path)
    print(f"Estimated output size: {estimated_size / 1024:.2f} KB")

    # Perform a quick size check of all text files
    total_size = sum(os.path.getsize(os.path.join(dirpath, f)) 
                     for dirpath, _, filenames in os.walk(args.path) 
                     for f in filenames if is_text_file(os.path.join(dirpath, f)))

    if estimated_size / 1024 > args.max_size:
        print(Fore.YELLOW + f"\nWarning: The estimated output size ({estimated_size / 1024:.2f} KB) exceeds the maximum allowed size ({args.max_size} KB)." + Style.RESET_ALL)
        proceed = input_handler.get_input("Do you want to proceed? (y/n): ")
        if proceed != 'y':
            print(Fore.YELLOW + "Analysis aborted." + Style.RESET_ALL)
            sys.exit(0)
    elif total_size / 1024 > args.max_size * 2:  # Only show this if total size is significantly larger
        print(Fore.YELLOW + f"\nNote: The total size of all text files in the directory ({total_size / 1024:.2f} KB) is significantly larger than the estimated output size." + Style.RESET_ALL)
        print(Fore.YELLOW + "This is likely due to large files or directories that will be ignored in the analysis." + Style.RESET_ALL)

    try:
        data = analyze_directory(args.path, ignore_patterns, args.path, include_git=args.include_git, max_depth=args.max_depth)
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
        file_name = args.file or f"{os.path.basename(args.path)}_codebase_digest.{output_formatter.output_file_extension()}"
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