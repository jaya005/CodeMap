import streamlit as st
import graphviz
import os
import ast
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# --- 1. BACKEND LOGIC ---

def analyze_file_imports(file_path):
    if not os.path.exists(file_path):
        return set()
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
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

def get_python_files_map(directory):
    file_map = {}
    for root, _, files in os.walk(directory):
        if "venv" in root or ".git" in root or "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                module_name = os.path.splitext(file)[0]
                full_path = os.path.join(root, file)
                file_map[module_name] = full_path
    return file_map

def build_smart_dependency_graph(directory):
    local_files = get_python_files_map(directory)
    nodes = []
    edges = set()

    for current_module, file_path in local_files.items():
        nodes.append({"id": current_module, "path": file_path})
        raw_imports = analyze_file_imports(file_path)
        
        for imp in raw_imports:
            target_match = None
            if imp in local_files:
                target_match = imp
            else:
                parts = imp.split('.')
                if parts[-1] in local_files:
                    target_match = parts[-1]
                elif parts[0] in local_files:
                    target_match = parts[0]

            if target_match and target_match != current_module:
                edges.add((current_module, target_match))

    edges_list = [{"source": s, "target": t} for s, t in edges]
    return {"nodes": nodes, "edges": edges_list, "files_map": local_files}

# --- 2. AI AGENT ---

class CodeChangeAgent:
    def __init__(self, graph_data):
        self.graph_data = graph_data
        self.files_map = graph_data['files_map']
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")
        else:
            self.model = None

    def explain_code(self, file_paths, query):
        if not self.model:
            return "⚠️ Google API Key not found."
        
        context = ""
        for path in file_paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    context += f"\n--- FILE: {os.path.basename(path)} ---\n{f.read()}\n"
            except:
                continue

        edges_desc = "No dependencies detected."
        if self.graph_data['edges']:
            edges_desc = "\n".join([f"{e['source']} imports {e['target']}" for e in self.graph_data['edges']])

        potential_entry_points = [f for f in self.files_map.keys() if f in ['app', 'main', 'manage', 'wsgi']]
        entry_point_instruction = ""
        if potential_entry_points:
            entry_point_instruction = f"""
            CRITICAL ARCHITECTURE NOTE:
            The following modules are ENTRY POINTS: {potential_entry_points}.
            They are NOT redundant even if nothing imports them.
            """

        prompt = f"""
        You are a Senior Software Architect.
        {entry_point_instruction}
        
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

st.set_page_config(page_title="CodeMap Pro", layout="wide")
st.title("🗺️ CodeMap: Smart Architecture")

# Initialize Session State
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

st.sidebar.header("📁 Config")
project_path = st.sidebar.text_input("Project Path", value=os.getcwd())

if st.sidebar.button("🚀 Scan Codebase"):
    with st.spinner("Analyzing..."):
        graph_data = build_smart_dependency_graph(project_path)
        st.session_state['graph'] = graph_data
        st.session_state['agent'] = CodeChangeAgent(graph_data)
        st.session_state['chat_history'] = [] 
        st.success(f"Scanned {len(graph_data['nodes'])} files.")

# --- MAIN UI ---

if 'graph' in st.session_state:
    data = st.session_state['graph']
    
    # [FIX]: Use Radio Button instead of Tabs to force persistence
    view_mode = st.radio(
        "Navigate:", 
        ["🕸️ Architecture", "💬 Ask AI"], 
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.markdown("---") # Visual separator

    # --- VIEW 1: ARCHITECTURE ---
    if view_mode == "🕸️ Architecture":
        st.subheader("Dependency Graph")
        viz = graphviz.Digraph()
        viz.attr(rankdir='LR')
        viz.attr('node', shape='box', style='filled', fillcolor='#E0F7FA')
        for node in data['nodes']:
            viz.node(node['id'], node['id'])
        for edge in data['edges']:
            viz.edge(edge['source'], edge['target'])
        st.graphviz_chart(viz)

    # --- VIEW 2: PERSISTENT CHAT ---
    elif view_mode == "💬 Ask AI":
        st.subheader("👩‍💻 Code Assistant")
        file_map = data['files_map']
        all_files_list = list(file_map.values())
        
        # Selection Input
        selected = st.multiselect("Select Context (Empty = All Files):", all_files_list, format_func=os.path.basename)
        
        # Display Chat History
        for msg in st.session_state['chat_history']:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input Form
        with st.form(key="ask_form"):
            user_query = st.text_input("Ask a question:", placeholder="e.g. Which files are redundant?")
            submit_button = st.form_submit_button("Ask AI")
            
            if submit_button and user_query:
                agent = st.session_state['agent']
                target_files = selected if selected else all_files_list
                
                # Show User Query
                with st.chat_message("user"):
                    st.markdown(user_query)
                st.session_state['chat_history'].append({"role": "user", "content": user_query})
                
                # Get AI Response
                with st.spinner("Thinking..."):
                    response = agent.explain_code(target_files, user_query)
                    
                    # Show AI Response
                    with st.chat_message("assistant"):
                        st.markdown(response)
                    st.session_state['chat_history'].append({"role": "assistant", "content": response})