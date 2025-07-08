import os
import json
import argparse
from tree_sitter_language_pack import get_language, get_parser
from tree_sitter import Parser

# --- Configuration ---
VALID_CPP_EXTENSIONS = {".h", ".cpp", ".i"}
VALID_PYTHON_EXTENSIONS = {".py"}

# --- Tree-sitter Query Strings ---
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
        capture_names = info['capture_names']
        if not query_str or not capture_names: continue
        try:
            query = lang_obj.query(query_str)
            captures_dict = query.captures(tree.root_node)
            for capture_name_in_query in capture_names:
                if capture_name_in_query in captures_dict:
                    for node in captures_dict[capture_name_in_query]:
                        text_to_add = get_node_text(node, content_bytes)
                        if data_key in ['includes', 'imports']:
                            text_to_add = text_to_add.strip('"<>')
                        file_data[data_key].append(text_to_add)
        except Exception as e:
            print(f"Error executing query for '{data_key}': {e}")
    for key in file_data:
        file_data[key] = sorted(list(set(file_data[key])))
    return file_data

# --- Main Logic ---
def main():
    parser = argparse.ArgumentParser(description="Analyze repository structure using tree-sitter.")
    parser.add_argument("--src-dir", default="./src", help="Directory containing source files.")
    parser.add_argument("--output-json", default="./repo_structure.json", help="Path for the output JSON file.")
    args = parser.parse_args()
    
    src_dir = args.src_dir
    output_json = args.output_json

    print("Loading languages from tree-sitter-language-pack...")
    try:
        cpp_lang_obj = get_language('cpp')
        cpp_parser = get_parser('cpp')
        python_lang_obj = get_language('python')
        python_parser = get_parser('python')
        print("C++ and Python languages loaded.")
    except Exception as e:
        print(f"Error loading languages: {e}")
        return

    cpp_query_definitions = {
        'includes': {'query_string': CPP_INCLUDE_QUERY_STR, 'capture_names': ['include_path']},
        'functions': {'query_string': CPP_FUNCTION_QUERY_STR, 'capture_names': ['function_name']},
        'classes': {'query_string': CPP_CLASS_QUERY_STR, 'capture_names': ['class_name']}
    }
    python_query_definitions = {
        'imports': {'query_string': PYTHON_IMPORT_QUERY_STR, 'capture_names': ['module_part', 'name_part']},
        'functions': {'query_string': PYTHON_FUNCTION_QUERY_STR, 'capture_names': ['function_name']},
        'classes': {'query_string': PYTHON_CLASS_QUERY_STR, 'capture_names': ['class_name']}
    }

    repo_structure = {}
    if not os.path.exists(src_dir):
        print(f"Source directory '{src_dir}' not found.")
        return

    print(f"Analyzing repository structure in '{src_dir}'...")
    file_count = 0
    for root, _, files in os.walk(src_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            _, extension = os.path.splitext(filename)

            current_parser = None
            current_query_definitions = None
            current_lang_obj = None
            
            if extension in VALID_CPP_EXTENSIONS:
                current_parser = cpp_parser
                current_query_definitions = cpp_query_definitions
                current_lang_obj = cpp_lang_obj
            elif extension in VALID_PYTHON_EXTENSIONS:
                current_parser = python_parser
                current_query_definitions = python_query_definitions
                current_lang_obj = python_lang_obj
            else:
                continue
            
            file_count += 1
            try:
                with open(file_path, 'rb') as f:
                    content_bytes = f.read()
                
                if not content_bytes.strip():
                    print(f"File {file_path} is empty. Skipping analysis.")
                    repo_structure[file_path] = {'error': 'empty file'}
                    continue
                
                analysis_result = parse_file_data(current_parser, content_bytes, current_query_definitions, current_lang_obj)
                repo_structure[file_path] = analysis_result
            except Exception as e:
                print(f"Error analyzing file {file_path}: {e}")
                repo_structure[file_path] = {'error': str(e)}

    try:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(repo_structure, f, indent=4)
        print(f"Repository structure analysis saved to {output_json}")
        print(f"Analyzed {file_count} files.")
    except Exception as e:
        print(f"Error writing to {output_json}: {e}")

if __name__ == "__main__":
    main() 