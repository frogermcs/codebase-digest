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