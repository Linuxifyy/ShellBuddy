#!/usr/bin/env python3
import os
import json
import re
import subprocess
from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown

# --- Externe API Imports ---
# Importeer de benodigde bibliotheken, maar faal niet als ze ontbreken.
try:
    import google.generativeai as genai
except ImportError:
    print("Waarschuwing: Google Gemini API niet geïmporteerd. Installeer met 'pip install google-genai'.")
    genai = None

try:
    from openai import OpenAI
except ImportError:
    print("Waarschuwing: OpenAI API niet geïmporteerd. Installeer met 'pip install openai'.")
    OpenAI = None

# --- Setup & Configuratie Lading ---
console = Console()
CONFIG_PATH = "config.json"

try:
    with open(CONFIG_PATH) as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    console.print(f"[bold red]❌ Configuratiebestand {CONFIG_PATH} niet gevonden.[/bold red]")
    exit(1)
except json.JSONDecodeError:
    console.print(f"[bold red]❌ Fout bij het lezen van {CONFIG_PATH}. Is het geldige JSON?[/bold red]")
    exit(1)

# Haal configuratiewaarden op
API_PROVIDER = CONFIG.get("api_provider", "gemini").lower()
MODEL_NAME = CONFIG.get("model", "gemini-2.5-flash")
LOG_DIR = CONFIG.get("log_dir", "logs") # Nieuw: log directory uit config

# --- API Initialisatie ---
if API_PROVIDER == "gemini":
    API_KEY = os.getenv("GEMINI_API_KEY") or CONFIG.get("api_keys", {}).get("GEMINI_API_KEY")
    if not API_KEY:
        console.print("[bold red]❌ GEMINI_API_KEY niet ingesteld in omgeving of 'config.json'.[/bold red]")
        exit(1)
    if not genai:
        console.print("[bold red]❌ De 'google-genai' bibliotheek is vereist voor Gemini, maar niet geïnstalleerd.[/bold red]")
        exit(1)
    genai.configure(api_key=API_KEY)
    client = None
    
elif API_PROVIDER == "openai":
    API_KEY = os.getenv("OPENAI_API_KEY") or CONFIG.get("api_keys", {}).get("OPENAI_API_KEY")
    if not API_KEY:
        console.print("[bold red]❌ OPENAI_API_KEY niet ingesteld in omgeving of 'config.json'.[/bold red]")
        exit(1)
    if not OpenAI:
        console.print("[bold red]❌ De 'openai' bibliotheek is vereist voor OpenAI, maar niet geïnstalleerd.[/bold red]")
        exit(1)
    client = OpenAI(api_key=API_KEY)
    
else:
    console.print(f"[bold red]❌ Onbekende API-provider: {API_PROVIDER}. Gebruik 'gemini' of 'openai'.[/bold red]")
    exit(1)

# Zorg ervoor dat de log map bestaat
os.makedirs(LOG_DIR, exist_ok=True)
def log_event(command, output):
    """Logt een uitgevoerd commando en de output naar een bestand."""
    # Deze simpele log functie is hier geplaatst om de afhankelijkheid van utils.py te verwijderen
    try:
        log_file = os.path.join(LOG_DIR, "session_log.txt")
        with open(log_file, "a") as f:
            f.write(f"[{os.getcwd()}] > {command}\n")
            f.write(f"{output}\n---\n")
    except Exception as e:
        console.print(f"[red]Fout bij loggen: {e}[/red]")

# --- Tool Functies (Onveranderd) ---
def detect_distro():
    """Detects the Linux distribution."""
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('ID='):
                    return line.strip().split('=')[1].strip('"').lower()
    except Exception:
        return 'unknown'
    return 'unknown'

DISTRO = detect_distro()

# --- AI Core Logica (Aangepaste get_ai_response) ---
SYSTEM_PROMPT = f"""
You are 'Companion', an expert AI Linux assistant operating inside a terminal.
You communicate in **English**.
Your goal is to guide the user step-by-step to solve their tasks, like an interactive shell expert.

YOUR WORKFLOW IS A LOOP:
1.  The user (USER) provides a task or problem.
2.  You respond (AI) with a **brief explanation** of your thinking and propose the *next* logical command(s) inside a ```bash code block.
3.  The script executes the command and provides the output (TOOL_OUTPUT).
4.  You analyze this output, provide a *new* explanation (AI), and propose the *next* command in a ```bash code block.
5.  Repeat this (explanation, command, output, explanation, command, output...) until the task is solved.
6.  When the task is solved or you have no more commands, provide a final report and an **empty** ```bash code block.
7.  If the user interrupts with a chat message instead of a command confirmation, that message will appear in the input. Respond to it appropriately.

RULES:
- Your response MUST ALWAYS consist of: Explanation (Markdown) FOLLOWED BY a code block (```bash ... ```).
- Propose commands step-by-step. One logical action per turn.
- Use 'sudo' where necessary.
- The 'cd' command is supported.
- DO NOT use interactive commands (like 'sudo -i', 'nano', 'vim', or those requiring runtime input).
- Current Linux distribution: {DISTRO}
"""

def get_ai_response(chat_history):
    """Fetches the next response from the selected AI model."""
    if API_PROVIDER == "gemini":
        model_instance = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_PROMPT)
        gemini_history = [{'role': h['role'], 'parts': h['parts']} for h in chat_history]
        response = model_instance.generate_content(gemini_history)
        return response.text
    
    elif API_PROVIDER == "openai":
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in chat_history:
            messages.append({"role": h['role'], "content": h['parts'][0]})
            
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7
        )
        return completion.choices[0].message.content

# --- Overige functies (parse_ai_response, execute_command, parse_selection) blijven ongewijzigd van v4.0 ---

def parse_ai_response(text):
    """Splits the AI response into explanation and commands."""
    explanation = text.strip()
    commands = []
    match = re.search(r"```bash\n(.*?)\n```", text, re.DOTALL)
    if match:
        explanation = text.split("```bash")[0].strip()
        commands_str = match.group(1).strip()
        commands = [cmd.strip() for cmd in commands_str.splitlines() if cmd.strip()]
    return explanation, commands

def execute_command(command):
    """Executes a single shell command, with special handling for 'cd'."""
    command = command.strip()
    if command.startswith("cd "):
        try:
            target_dir = command[3:].strip() or "~"
            expanded_dir = os.path.expanduser(target_dir)
            os.chdir(expanded_dir)
            return f"✅ (Working directory changed to: {os.getcwd()})"
        except Exception as e:
            return f"⚠️ Error in 'cd': {e}"
    try:
        result = subprocess.run(
            command, shell=True, text=True, capture_output=True, timeout=30, stdin=subprocess.DEVNULL 
        )
        output = result.stdout.strip() + "\n" + result.stderr.strip()
        return (output.strip() or '✅ (Command executed, no output)')
    except subprocess.TimeoutExpired:
        return f"⚠️ Command '{command}' timed out (waiting for input?)"
    except Exception as e:
        return f"⚠️ Execution error: {e}"

def parse_selection(selection_str, max_num):
    """Parses a selection string (e.g., '1,3-5') to a list of 0-based indices."""
    indices = set()
    parts = selection_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if 1 <= start <= end <= max_num:
                    indices.update(range(start - 1, end)) 
            except ValueError: continue
        else:
            try:
                num = int(part)
                if 1 <= num <= max_num:
                    indices.add(num - 1)
            except ValueError: continue
    return sorted(list(indices))

# --- Main Functie (Onveranderd, gebruikt nu de nieuwe setup) ---
def main():
    console.print(f"[cyan]Detected Linux Distribution:[/cyan] {DISTRO}")
    console.print(f"[cyan]Using API:[/cyan] {API_PROVIDER.upper()} ([dim]{MODEL_NAME}[/dim])")
    console.print("[bold cyan]🧠 Ultimate AI Terminal Companion (v4.1 - Consolidated Config)[/bold cyan]\n")
    
    chat_history = []
    
    while True:
        cwd = os.getcwd()
        user_input = Prompt.ask(f"[dim]({cwd})[/dim]\n[green]You:[/green]")
        if user_input.lower() in {"exit", "quit"}:
            console.print("👋 See you later!")
            break

        chat_history.append({'role': 'user', 'parts': [user_input]})
        
        ai_is_working = True
        while ai_is_working:
            try:
                ai_response_text = get_ai_response(chat_history)
                explanation, commands = parse_ai_response(ai_response_text)
                
                chat_history.append({'role': 'model', 'parts': [ai_response_text]})

                console.print("\n[bold cyan]🤖 Companion:[/bold cyan]")
                console.print(Markdown(explanation))

                if not commands:
                    ai_is_working = False
                    continue 

                console.print("[bold yellow]Suggested commands:[/bold yellow]")
                for i, cmd in enumerate(commands, 1):
                    console.print(f"  {i}. [cyan]{cmd}[/cyan]")
                
                console.print("\n[bold]Action:[/bold] [green]y[/green] (all), [red]n[/red] (skip), [cyan]Numbers[/cyan] (select) or type a chat message to interrupt.")
                keuze = Prompt.ask("[green]Choice[/green]", default="y").lower()
                
                to_execute = []
                tool_output_str = ""

                if keuze == 'y' or keuze == 'yes':
                    to_execute = commands
                elif keuze == 'n' or keuze == 'no':
                    tool_output_str = "TOOL_OUTPUT:\n(Commands skipped by user)"
                else:
                    selected_indices = parse_selection(keuze, len(commands))
                    if selected_indices:
                        to_execute = [commands[i] for i in selected_indices]
                    else:
                        console.print("🤖 Understood, interrupting with new input.")
                        chat_history.append({'role': 'user', 'parts': [keuze]})
                        continue

                if to_execute:
                    executed_outputs = []
                    for cmd in to_execute:
                        console.print(f"\n[bold yellow]▶️  Executing:[/bold yellow] [cyan]{cmd}[/cyan]")
                        output = execute_command(cmd)
                        
                        if output.startswith("✅"): console.print(f"[green]{output}[/green]")
                        elif output.startswith("⚠️"): console.print(f"[red]{output}[/red]")
                        else: console.print(f"[dim]{output}[/dim]")
                        
                        log_event(cmd, output)
                        executed_outputs.append(f"$ {cmd}\n{output}")
                    
                    tool_output_str = f"TOOL_OUTPUT:\n" + "\n".join(executed_outputs)

                if tool_output_str:
                    chat_history.append({'role': 'user', 'parts': [tool_output_str]})
                
            except Exception as e:
                console.print(f"[bold red]❌ An error occurred in the AI loop: {e}[/bold red]")
                ai_is_working = False

if __name__ == "__main__":
    main()
