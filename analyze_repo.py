import os
import json
# from tree_sitter import Language, Parser # No longer needed directly for language loading
from tree_sitter_language_pack import get_language, get_parser
from tree_sitter import Parser # We still need Parser itself

# --- Configuration ---
SRC_DIR = "./src"
OUTPUT_JSON = "./repo_structure.json"

VALID_CPP_EXTENSIONS = {".h", ".cpp", ".i"} # .i files will be parsed as C++
VALID_PYTHON_EXTENSIONS = {".py"} # Retaining for completeness, though not in current src

# --- Tree-sitter Query Strings ---
# Note: Capture names (e.g., @include_path) are used as keys in the captures dictionary.
CPP_INCLUDE_QUERY_STR = """
(preproc_include path: (string_literal) @include_path)
(preproc_include path: (system_lib_string) @include_path)
"""
CPP_FUNCTION_QUERY_STR = """
(function_definition declarator: (function_declarator declarator: (identifier) @function_name))
(function_definition declarator: (identifier) @function_name)
"""
CPP_CLASS_QUERY_STR = """
(class_specifier name: (type_identifier) @class_name)
(struct_specifier name: (type_identifier) @class_name)
"""

PYTHON_IMPORT_QUERY_STR = """
(import_statement name: (dotted_name (identifier) @module_part)) @import_statement
(import_from_statement module_name: (dotted_name (identifier) @module_part) name: (dotted_name (identifier) @name_part) @import_from_statement)
; We capture @module_part for simple imports, and both for from_imports.
; For from_imports, we might want to combine module_part and name_part later.
"""
PYTHON_FUNCTION_QUERY_STR = "(function_definition name: (identifier) @function_name)"
PYTHON_CLASS_QUERY_STR = "(class_definition name: (identifier) @class_name)"

# --- Helper Functions ---
def get_node_text(node, content_bytes):
    return content_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')

def parse_file_data(parser, content_bytes, query_definitions, lang_obj):
    tree = parser.parse(content_bytes)
    file_data = {}

    for data_key, info in query_definitions.items():
        file_data[data_key] = []
        query_str = info['query_string']
        capture_names = info['capture_names'] # List of capture names for this query type
        if not query_str or not capture_names: continue
        
        try:
            query = lang_obj.query(query_str)
            captures_dict = query.captures(tree.root_node) # Dict[str, List[Node]]
            
            for capture_name_in_query in capture_names:
                if capture_name_in_query in captures_dict:
                    for node in captures_dict[capture_name_in_query]:
                        text_to_add = get_node_text(node, content_bytes)
                        if data_key == 'includes' or data_key == 'imports': # Special handling for paths
                            text_to_add = text_to_add.strip('"<>')
                        file_data[data_key].append(text_to_add)
        except Exception as e:
            print(f"Error executing query for '{data_key}' (capture '{capture_names}'): {type(e).__name__} - {e}")
    
    for key in file_data:
        file_data[key] = sorted(list(set(file_data[key])))
    return file_data

# --- Main Logic ---
def main():
    print("Loading languages from tree-sitter-language-pack...")
    try:
        # tree-sitter-language-pack uses 'cpp' for C++ and 'python' for Python
        cpp_lang_obj = get_language('cpp') 
        cpp_parser = get_parser('cpp') # This sets the language on the parser
        print("C++ language and parser loaded.")
        
        python_lang_obj = None
        python_parser = None
        # To enable Python:
        # python_lang_obj = get_language('python')
        # python_parser = get_parser('python')
        # print("Python language and parser loaded.")

    except Exception as e:
        print(f"Error loading languages/parsers from tree-sitter-language-pack: {e}")
        print("Ensure 'tree-sitter-language-pack' is installed correctly.")
        return

    # Define what to extract for each language
    # Each key (e.g., 'includes') will be a list in the output JSON.
    # 'capture_names' lists the @capture_name strings from the query that contribute to this list.
    cpp_query_definitions = {
        'includes':  {'query_string': CPP_INCLUDE_QUERY_STR,  'capture_names': ['include_path']},
        'functions': {'query_string': CPP_FUNCTION_QUERY_STR, 'capture_names': ['function_name']},
        'classes':   {'query_string': CPP_CLASS_QUERY_STR,    'capture_names': ['class_name']}
    }
    python_query_definitions = {
        'imports':   {'query_string': PYTHON_IMPORT_QUERY_STR, 'capture_names': ['module_part', 'name_part']},
        'functions': {'query_string': PYTHON_FUNCTION_QUERY_STR, 'capture_names': ['function_name']},
        'classes':   {'query_string': PYTHON_CLASS_QUERY_STR,    'capture_names': ['class_name']}
    }

    repo_structure = {}

    if not os.path.exists(SRC_DIR):
        print(f"Source directory '{SRC_DIR}' not found.")
        return

    print(f"Analyzing repository structure in '{SRC_DIR}'...")
    file_count = 0
    for root, _, files in os.walk(SRC_DIR):
        for filename in files:
            file_path = os.path.join(root, filename)
            _, extension = os.path.splitext(filename)

            current_parser = None
            current_query_definitions = None
            current_lang_obj = None
            output_data_template = {'includes': [], 'functions': [], 'classes': [], 'error': None}

            if extension in VALID_CPP_EXTENSIONS:
                current_parser = cpp_parser
                current_query_definitions = cpp_query_definitions
                current_lang_obj = cpp_lang_obj
                print(f"Analyzing C++-like file: {file_path}")
            elif extension in VALID_PYTHON_EXTENSIONS and python_parser:
                current_parser = python_parser
                current_query_definitions = python_query_definitions
                current_lang_obj = python_lang_obj
                output_data_template = {'imports': [], 'functions': [], 'classes': [], 'error': None}
                print(f"Analyzing Python file: {file_path}")
            else:
                continue
            
            file_count += 1
            try:
                with open(file_path, 'rb') as f:
                    content_bytes = f.read()
                if not content_bytes.strip():
                    print(f"File {file_path} is empty. Skipping analysis.")
                    entry = {**output_data_template, 'error': 'empty file'}
                    del entry['error'] # No, keep error, but ensure other keys are list
                    for k in entry: entry[k] = [] if k != 'error' else 'empty file' 
                    repo_structure[file_path] = entry
                    continue
                
                analysis_result = parse_file_data(current_parser, content_bytes, current_query_definitions, current_lang_obj)
                repo_structure[file_path] = analysis_result

            except Exception as e:
                print(f"Error analyzing file {file_path}: {type(e).__name__} - {e}")
                entry = {**output_data_template, 'error': str(e)}
                for k in entry: entry[k] = [] if k != 'error' else str(e)
                repo_structure[file_path] = entry

    if not repo_structure:
        print("No valid source files found to analyze.")
        return

    try:
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(repo_structure, f, indent=4)
        print(f"Repository structure analysis saved to {OUTPUT_JSON}")
        print(f"Analyzed {file_count} files.")
    except Exception as e:
        print(f"Error writing repository structure to {OUTPUT_JSON}: {e}")

if __name__ == "__main__":
    main() 