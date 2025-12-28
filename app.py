# import streamlit as st
# import graphviz
# import os
# import ast
# import google.generativeai as genai
# from dotenv import load_dotenv

# load_dotenv()

# # --- 1. BACKEND LOGIC ---

# def analyze_file_imports(file_path):
#     if not os.path.exists(file_path):
#         return set()
#     with open(file_path, "r", encoding="utf-8") as f:
#         try:
#             tree = ast.parse(f.read())
#         except Exception:
#             return set()

#     imported_names = set()
#     for node in ast.walk(tree):
#         if isinstance(node, ast.Import):
#             for alias in node.names:
#                 imported_names.add(alias.name)
#         elif isinstance(node, ast.ImportFrom):
#             if node.module:
#                 imported_names.add(node.module)
#                 for name in node.names:
#                     imported_names.add(name.name)
#                     imported_names.add(f"{node.module}.{name.name}")
#     return imported_names

# def get_python_files_map(directory):
#     file_map = {}
#     for root, _, files in os.walk(directory):
#         if "venv" in root or ".git" in root or "__pycache__" in root:
#             continue
#         for file in files:
#             if file.endswith(".py") and file != "__init__.py":
#                 module_name = os.path.splitext(file)[0]
#                 full_path = os.path.join(root, file)
#                 file_map[module_name] = full_path
#     return file_map

# def build_smart_dependency_graph(directory):
#     local_files = get_python_files_map(directory)
#     nodes = []
#     edges = set()

#     for current_module, file_path in local_files.items():
#         nodes.append({"id": current_module, "path": file_path})
#         raw_imports = analyze_file_imports(file_path)
        
#         for imp in raw_imports:
#             target_match = None
#             if imp in local_files:
#                 target_match = imp
#             else:
#                 parts = imp.split('.')
#                 if parts[-1] in local_files:
#                     target_match = parts[-1]
#                 elif parts[0] in local_files:
#                     target_match = parts[0]

#             if target_match and target_match != current_module:
#                 edges.add((current_module, target_match))

#     edges_list = [{"source": s, "target": t} for s, t in edges]
#     return {"nodes": nodes, "edges": edges_list, "files_map": local_files}

# # --- 2. AI AGENT ---

# class CodeChangeAgent:
#     def __init__(self, graph_data):
#         self.graph_data = graph_data
#         self.files_map = graph_data['files_map']
        
#         api_key = os.getenv("GOOGLE_API_KEY")
#         if api_key:
#             genai.configure(api_key=api_key)
#             self.model = genai.GenerativeModel("gemini-2.5-flash")
#         else:
#             self.model = None

#     def explain_code(self, file_paths, query):
#         if not self.model:
#             return "⚠️ Google API Key not found."
        
#         context = ""
#         for path in file_paths:
#             try:
#                 with open(path, "r", encoding="utf-8") as f:
#                     context += f"\n--- FILE: {os.path.basename(path)} ---\n{f.read()}\n"
#             except:
#                 continue

#         edges_desc = "No dependencies detected."
#         if self.graph_data['edges']:
#             edges_desc = "\n".join([f"{e['source']} imports {e['target']}" for e in self.graph_data['edges']])

#         potential_entry_points = [f for f in self.files_map.keys() if f in ['app', 'main', 'manage', 'wsgi']]
#         entry_point_instruction = ""
#         if potential_entry_points:
#             entry_point_instruction = f"""
#             CRITICAL ARCHITECTURE NOTE:
#             The following modules are ENTRY POINTS: {potential_entry_points}.
#             They are NOT redundant even if nothing imports them.
#             """

#         prompt = f"""
#         You are a Senior Software Architect.
#         {entry_point_instruction}
        
#         PROJECT ARCHITECTURE:
#         {edges_desc}
        
#         SOURCE CODE:
#         {context}
        
#         USER QUESTION: {query}
#         """
#         try:
#             return self.model.generate_content(prompt).text
#         except Exception as e:
#             return f"Error: {e}"

# # --- 3. UI SETUP ---

# st.set_page_config(page_title="CodeMap Pro", layout="wide")
# st.title("🗺️ CodeMap: Smart Architecture")

# # Initialize Session State
# if 'chat_history' not in st.session_state:
#     st.session_state['chat_history'] = []

# st.sidebar.header("📁 Config")
# project_path = st.sidebar.text_input("Project Path", value=os.getcwd())

# if st.sidebar.button("🚀 Scan Codebase"):
#     with st.spinner("Analyzing..."):
#         graph_data = build_smart_dependency_graph(project_path)
#         st.session_state['graph'] = graph_data
#         st.session_state['agent'] = CodeChangeAgent(graph_data)
#         st.session_state['chat_history'] = [] 
#         st.success(f"Scanned {len(graph_data['nodes'])} files.")

# # --- MAIN UI ---

# if 'graph' in st.session_state:
#     data = st.session_state['graph']
    
#     # [FIX]: Use Radio Button instead of Tabs to force persistence
#     view_mode = st.radio(
#         "Navigate:", 
#         ["🕸️ Architecture", "💬 Ask AI"], 
#         horizontal=True,
#         label_visibility="collapsed"
#     )
    
#     st.markdown("---") # Visual separator

#     # --- VIEW 1: ARCHITECTURE ---
#     if view_mode == "🕸️ Architecture":
#         st.subheader("Dependency Graph")
#         viz = graphviz.Digraph()
#         viz.attr(rankdir='LR')
#         viz.attr('node', shape='box', style='filled', fillcolor='#E0F7FA')
#         for node in data['nodes']:
#             viz.node(node['id'], node['id'])
#         for edge in data['edges']:
#             viz.edge(edge['source'], edge['target'])
#         st.graphviz_chart(viz)

#     # --- VIEW 2: PERSISTENT CHAT ---
#     elif view_mode == "💬 Ask AI":
#         st.subheader("👩‍💻 Code Assistant")
#         file_map = data['files_map']
#         all_files_list = list(file_map.values())
        
#         # Selection Input
#         selected = st.multiselect("Select Context (Empty = All Files):", all_files_list, format_func=os.path.basename)
        
#         # Display Chat History
#         for msg in st.session_state['chat_history']:
#             with st.chat_message(msg["role"]):
#                 st.markdown(msg["content"])

#         # Input Form
#         with st.form(key="ask_form"):
#             user_query = st.text_input("Ask a question:", placeholder="e.g. Which files are redundant?")
#             submit_button = st.form_submit_button("Ask AI")
            
#             if submit_button and user_query:
#                 agent = st.session_state['agent']
#                 target_files = selected if selected else all_files_list
                
#                 # Show User Query
#                 with st.chat_message("user"):
#                     st.markdown(user_query)
#                 st.session_state['chat_history'].append({"role": "user", "content": user_query})
                
#                 # Get AI Response
#                 with st.spinner("Thinking..."):
#                     response = agent.explain_code(target_files, user_query)
                    
#                     # Show AI Response
#                     with st.chat_message("assistant"):
#                         st.markdown(response)
#                     st.session_state['chat_history'].append({"role": "assistant", "content": response})
import streamlit as st
import graphviz
import ast
import os
import zipfile
import google.generativeai as genai
from dotenv import load_dotenv

try:
    load_dotenv()
except:
    pass

# --- 1. ROBUST IMPORT RESOLVER ---

def normalize_path_to_module(path):
    """Converts file path to python module path: 'folder/sub/file.py' -> 'folder.sub.file'"""
    return path.replace("\\", "/").replace("/", ".").replace(".py", "")

def get_parent_package(module_name, level):
    """Calculates parent package for relative imports (..utils)"""
    parts = module_name.split(".")
    if len(parts) < level:
        return ""
    return ".".join(parts[:-level])

def resolve_import(import_name, current_module, all_modules, level=0):
    """
    STRICT Python Import Resolution Logic.
    
    1. Handle Relative Imports (level > 0):
       - If inside 'pkg.sub.module' and imports '..utils', look for 'pkg.utils'.
       
    2. Handle Absolute Imports (level == 0):
       - Exact Match: 'scrapers.run' -> matches 'scrapers.run'.
       - Root Handling: If user uploaded 'project/scrapers/run.py' but code says 'import scrapers.run',
         we detect that 'project' is just a container and match 'scrapers.run' inside it.
    """
    target = None

    # --- CASE 1: Relative Import (from . import x or from .. import y) ---
    if level > 0:
        parent_package = get_parent_package(current_module, level)
        if parent_package:
            # Candidate: parent.x
            candidate = f"{parent_package}.{import_name}" if import_name else parent_package
            
            # Check exact match
            if candidate in all_modules:
                return candidate
            
            # Check if it's a package (folder) importing a module inside it
            # e.g. 'from .' import 'utils' inside 'pkg' might mean 'pkg.utils'
            candidate_sub = f"{candidate}.{import_name}" if import_name else candidate
            if candidate_sub in all_modules:
                return candidate_sub

    # --- CASE 2: Absolute Import (import x or from x import y) ---
    else:
        # 2a. Direct Match (The perfect scenario)
        if import_name in all_modules:
            return import_name

        # 2b. "Source Root" Simulation (The Fix for your issue)
        # If user uploaded 'price_comp/scrapers/run.py' (module: price_comp.scrapers.run)
        # But code imports 'scrapers.run'
        # We check if any module *ends with* the import name AND follows the path structure.
        
        for candidate in all_modules:
            # Logic: If candidate is 'price_comp.scrapers.run' and import is 'scrapers.run'
            # Check if it ends with it.
            if candidate.endswith(f".{import_name}"):
                return candidate
            
            # Logic: If import is just 'scrapers', look for 'price_comp.scrapers.__init__' or just matching folder logic
            # (Simplified for single files):
            if candidate.endswith(f".{import_name}"): 
                return candidate

    return None

def analyze_imports_from_string(source_code):
    """Extracts module imports using AST."""
    try:
        tree = ast.parse(source_code)
    except Exception:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({"name": alias.name, "level": 0})
        elif isinstance(node, ast.ImportFrom):
            level = node.level # 0=absolute, 1='.', 2='..'
            module = node.module or ""
            for alias in node.names:
                # Store enough info to reconstruct: 'from x import y' -> name='x.y'
                full_name = f"{module}.{alias.name}" if module else alias.name
                imports.append({"name": full_name, "level": level})
    return imports

def build_graph_from_uploads(uploaded_files):
    """
    Builds the dependency graph using STRICT resolution.
    """
    file_content_map = {}
    file_name_map = {} 
    
    # 1. READ FILES
    for uploaded_file in uploaded_files:
        content = None
        filename = uploaded_file.name

        if filename.endswith(".zip"):
            with zipfile.ZipFile(uploaded_file) as z:
                for z_name in z.namelist():
                    if z_name.endswith(".py") and not z_name.startswith("__MACOSX"):
                        with z.open(z_name) as f:
                            clean_id = normalize_path_to_module(z_name)
                            file_content_map[clean_id] = f.read().decode("utf-8")
                            file_name_map[clean_id] = z_name
        
        elif filename.endswith(".py"):
            filename = getattr(uploaded_file, "name", uploaded_file.name)
            clean_id = normalize_path_to_module(filename)
            try:
                file_content_map[clean_id] = uploaded_file.getvalue().decode("utf-8")
                file_name_map[clean_id] = filename
            except:
                pass

    all_modules = set(file_content_map.keys())
    nodes = []
    edges = set()

    # 2. CREATE NODES
    for module_id in file_content_map:
        nodes.append({"id": module_id, "label": os.path.basename(file_name_map[module_id])})

    # 3. RESOLVE IMPORTS (The Smart Part)
    for current_module, source_code in file_content_map.items():
        raw_imports = analyze_imports_from_string(source_code)
        
        for imp_data in raw_imports:
            # Try to resolve 'import x' to a real file in our list
            target = resolve_import(imp_data["name"], current_module, all_modules, imp_data["level"])
            
            # If explicit match failed, try splitting (e.g. import x.y.z -> maybe x.y is the file)
            if not target and "." in imp_data["name"] and imp_data["level"] == 0:
                parts = imp_data["name"].split(".")
                for i in range(len(parts)-1, 0, -1):
                    sub_import = ".".join(parts[:i])
                    target = resolve_import(sub_import, current_module, all_modules, 0)
                    if target:
                        break

            if target and target != current_module:
                edges.add((current_module, target))

    edges_list = [{"source": s, "target": t} for s, t in edges]
    
    return {
        "nodes": nodes, 
        "edges": edges_list, 
        "content_map": file_content_map, 
        "name_map": file_name_map
    }

# --- 2. ROBUST AI AGENT ---

class CodeChangeAgent:
    def __init__(self, graph_data):
        self.graph_data = graph_data
        self.content_map = graph_data['content_map']
        
        api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")
            self.backup_model = genai.GenerativeModel("gemini-pro")
        else:
            self.model = None

    def explain_code(self, selected_modules, query):
        if not self.model:
            return "⚠️ Google API Key not found. Please add it to Streamlit Secrets."
        
        context = ""
        for module in selected_modules:
            code = self.content_map.get(module, "")
            filename = self.graph_data['name_map'].get(module, module)
            context += f"\n--- FILE: {filename} ---\n{code}\n"

        edges_desc = "No dependencies detected."
        if self.graph_data['edges']:
            edges_desc = "\n".join([f"{e['source']} imports {e['target']}" for e in self.graph_data['edges']])

        prompt = f"""
        You are a Senior Software Architect.
        PROJECT ARCHITECTURE: {edges_desc}
        SOURCE CODE: {context}
        USER QUESTION: {query}
        """

        try:
            return self.model.generate_content(prompt).text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                try:
                    return f"⚠️ Quota exceeded. Using backup model...\n\n" + \
                           self.backup_model.generate_content(prompt).text
                except:
                    return "❌ **Daily Quota Exceeded**."
            return f"⚠️ Error: {error_msg}"

# --- 3. UI SETUP ---

st.set_page_config(page_title="CodeMap Cloud", layout="wide")
st.title("☁️ CodeMap: Cloud Architecture")

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

st.sidebar.header("📂 Project Upload")
uploaded_files = st.sidebar.file_uploader(
    "Upload .zip or drag folder:", 
    accept_multiple_files=True, 
    type=["py", "zip"]
)

if uploaded_files:
    if st.sidebar.button("🚀 Analyze"):
        with st.spinner("Analyzing..."):
            graph_data = build_graph_from_uploads(uploaded_files)
            if not graph_data['nodes']:
                st.error("No Python files found!")
            else:
                st.session_state['graph'] = graph_data
                st.session_state['agent'] = CodeChangeAgent(graph_data)
                st.session_state['chat_history'] = []
                st.success(f"Analyzed {len(graph_data['nodes'])} modules!")

if 'graph' in st.session_state:
    data = st.session_state['graph']
    
    view_mode = st.radio("Menu:", ["🕸️ Architecture", "💬 Ask AI"], horizontal=True, label_visibility="collapsed")
    st.markdown("---") 

    if view_mode == "🕸️ Architecture":
        viz = graphviz.Digraph()
        viz.attr(rankdir='TB') 
        viz.attr('node', shape='box', style='filled', fillcolor='#E0F7FA', fontname='Arial')
        
        for node in data['nodes']:
            viz.node(node['id'], node['label'])
        for edge in data['edges']:
            viz.edge(edge['source'], edge['target'])
        st.graphviz_chart(viz)

    elif view_mode == "💬 Ask AI":
        all_modules = list(data['content_map'].keys())
        selected = st.multiselect("Select files:", all_modules, format_func=lambda x: data['name_map'][x])
        
        for msg in st.session_state['chat_history']:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        with st.form("ask_form"):
            query = st.text_input("Question:")
            if st.form_submit_button("Ask"):
                agent = st.session_state['agent']
                target = selected if selected else all_modules
                st.session_state['chat_history'].append({"role": "user", "content": query})
                with st.chat_message("user"): st.markdown(query)
                
                with st.spinner("Thinking..."):
                    resp = agent.explain_code(target, query)
                    st.session_state['chat_history'].append({"role": "assistant", "content": resp})
                    with st.chat_message("assistant"): st.markdown(resp)