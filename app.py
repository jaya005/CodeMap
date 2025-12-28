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
import io
import google.generativeai as genai
from dotenv import load_dotenv

# Try loading .env (Local), pass if fails (Cloud)
try:
    load_dotenv()
except:
    pass

# --- 1. BACKEND LOGIC (Handles Zip & Py) ---

def analyze_imports_from_string(source_code):
    """Parses imports from a string of code."""
    try:
        tree = ast.parse(source_code)
    except Exception:
        return set()

    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.add(node.module)
                for name in node.names:
                    imported_names.add(name.name)
                    imported_names.add(f"{node.module}.{name.name}")
    return imported_names

def process_file_content(filename, content_bytes, file_content_map, file_name_map):
    """Helper to decode and store file content."""
    try:
        # Create a clean module ID from path: 'src/utils/helper.py' -> 'src.utils.helper'
        clean_name = filename.replace("\\", "/").replace("/", ".").replace(".py", "")
        
        # Decode bytes to string
        source_code = content_bytes.decode("utf-8")
        
        file_content_map[clean_name] = source_code
        file_name_map[clean_name] = filename
    except Exception:
        pass # Skip binary or non-utf8 files

def build_graph_from_uploads(uploaded_files):
    """
    Handles both raw .py files AND .zip archives.
    """
    file_content_map = {}
    file_name_map = {} 

    for uploaded_file in uploaded_files:
        
        # CASE A: User uploaded a ZIP file (The best way to upload folders)
        if uploaded_file.name.endswith(".zip"):
            with zipfile.ZipFile(uploaded_file) as z:
                for filename in z.namelist():
                    if filename.endswith(".py") and not filename.startswith("__MACOSX"):
                        with z.open(filename) as f:
                            process_file_content(filename, f.read(), file_content_map, file_name_map)
                            
        # CASE B: User uploaded raw .py files
        elif uploaded_file.name.endswith(".py"):
            # Use the full path if browser provided it, else filename
            filename = getattr(uploaded_file, "name", uploaded_file.name)
            process_file_content(filename, uploaded_file.getvalue(), file_content_map, file_name_map)

    # --- Build Dependency Graph ---
    nodes = []
    edges = set()

    for current_module, source_code in file_content_map.items():
        nodes.append({"id": current_module, "filename": file_name_map[current_module]})
        
        raw_imports = analyze_imports_from_string(source_code)
        
        for imp in raw_imports:
            target_match = None
            
            # Logic 1: Exact Match (import utils)
            if imp in file_content_map:
                target_match = imp
            
            # Logic 2: Submodule Match (from utils import helper)
            else:
                parts = imp.split('.')
                # Check backwards: utils.helper.func -> check 'utils.helper', then 'utils'
                for i in range(len(parts), 0, -1):
                    candidate = ".".join(parts[:i])
                    if candidate in file_content_map:
                        target_match = candidate
                        break

            if target_match and target_match != current_module:
                edges.add((current_module, target_match))

    edges_list = [{"source": s, "target": t} for s, t in edges]
    
    return {
        "nodes": nodes, 
        "edges": edges_list, 
        "content_map": file_content_map,
        "name_map": file_name_map
    }

# --- 2. AI AGENT ---

class CodeChangeAgent:
    def __init__(self, graph_data):
        self.graph_data = graph_data
        self.content_map = graph_data['content_map']
        
        api_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        
        if api_key:
            genai.configure(api_key=api_key)
            # Use stable model
            self.model = genai.GenerativeModel("gemini-2.5-flash") 
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

        # Identify Entry Points
        entry_list = ['app', 'main', 'manage', 'wsgi', 'streamlit_app', 'cli']
        potential_entry_points = [m for m in self.content_map.keys() if any(e in m.lower() for e in entry_list)]
        
        entry_instruction = ""
        if potential_entry_points:
            entry_instruction = f"CRITICAL: The following are ENTRY POINTS (Apps): {potential_entry_points}. Do not call them redundant."

        prompt = f"""
        You are a Senior Software Architect.
        {entry_instruction}
        
        PROJECT ARCHITECTURE:
        {edges_desc}
        
        SOURCE CODE:
        {context}
        
        USER QUESTION: {query}
        """
        try:
            return self.model.generate_content(prompt).text
        except Exception as e:
            return f"Error: {e}"

# --- 3. UI SETUP ---

st.set_page_config(page_title="CodeMap Cloud", layout="wide")
st.title("☁️ CodeMap: Cloud Architecture")

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# --- SIDEBAR ---
st.sidebar.header("📂 Project Upload")
st.sidebar.info("💡 **Tip:** For best results, zip your folder and upload the **.zip** file!")

# Allow Zip OR Multiple Python files
uploaded_files = st.sidebar.file_uploader(
    "Upload .zip or .py files:", 
    accept_multiple_files=True, 
    type=["py", "zip"]
)

if uploaded_files:
    if st.sidebar.button("🚀 Analyze Files"):
        with st.spinner("Unzipping and Analyzing..."):
            graph_data = build_graph_from_uploads(uploaded_files)
            
            if not graph_data['nodes']:
                st.error("No Python files found! Did you upload a valid zip or .py files?")
            else:
                st.session_state['graph'] = graph_data
                st.session_state['agent'] = CodeChangeAgent(graph_data)
                st.session_state['chat_history'] = [] 
                st.success(f"Successfully analyzed {len(graph_data['nodes'])} modules!")
else:
    st.sidebar.info("👆 Upload a .zip of your project to start.")

# --- MAIN UI ---

if 'graph' in st.session_state:
    data = st.session_state['graph']
    
    # Navigation
    view_mode = st.radio(
        "Menu:", 
        ["🕸️ Architecture Map", "💬 Ask the Codebase"], 
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("---") 

    # VIEW 1
    if view_mode == "🕸️ Architecture Map":
        st.subheader("Dependency Graph")
        viz = graphviz.Digraph()
        viz.attr(rankdir='LR')
        viz.attr('node', shape='box', style='filled', fillcolor='#E0F7FA', fontname='Arial')
        
        for node in data['nodes']:
            viz.node(node['id'], node['filename'])
        for edge in data['edges']:
            viz.edge(edge['source'], edge['target'])
            
        st.graphviz_chart(viz)

    # VIEW 2
    elif view_mode == "💬 Ask the Codebase":
        st.subheader("👩‍💻 Onboarding Assistant")
        
        all_modules = list(data['content_map'].keys())
        selected_modules = st.multiselect(
            "Select files to discuss (Default = All):", 
            all_modules,
            format_func=lambda x: data['name_map'][x]
        )
        
        # History
        for msg in st.session_state['chat_history']:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input
        with st.form(key="ask_form", clear_on_submit=False):
            user_query = st.text_input("Ask a question:", placeholder="e.g., Which files are redundant?")
            submit_button = st.form_submit_button("Ask AI")
            
            if submit_button and user_query:
                agent = st.session_state['agent']
                target_modules = selected_modules if selected_modules else all_modules
                
                with st.chat_message("user"):
                    st.markdown(user_query)
                st.session_state['chat_history'].append({"role": "user", "content": user_query})
                
                with st.spinner("Analyzing..."):
                    response = agent.explain_code(target_modules, user_query)
                    
                    with st.chat_message("assistant"):
                        st.markdown(response)
                    st.session_state['chat_history'].append({"role": "assistant", "content": response})
