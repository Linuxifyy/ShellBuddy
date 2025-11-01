# ShellBuddy

**Ultimate Linux AI Companion for Your Terminal**

ShellBuddy is your interactive AI Linux companion that assists you directly in the terminal. It not only troubleshoots problems but can also guide, execute safe commands, locate files, install software, and help with scripts. The AI works step-by-step, executing commands and analyzing outputs to give actionable guidance.

---

## Features

* **Interactive AI Terminal Companion**: Chat with ShellBuddy and get intelligent step-by-step guidance.
* **Command Execution**: Safely runs Linux commands and uses the output to plan next steps.
* **File and System Operations**: Find files, check system info, manage directories, and more.
* **Distribution Awareness**: Detects your Linux distro and uses the correct commands.
* **Step-by-Step Workflow**: Proposes one command at a time and asks for confirmation before execution.
* **Logging**: All executed commands and outputs are logged.
* **Extensible AI Provider**: Supports Google Gemini and OpenAI (configurable).

---

## Installation

```bash
# Clone the repository
git clone https://github.com/Linuxifyy/ShellBuddy.git
cd ShellBuddy

# (Optional) Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Set your API key in the environment or in `config.json`:

```bash
export GEMINI_API_KEY="your_api_key_here"
# or for OpenAI
export OPENAI_API_KEY="your_api_key_here"
```

---

## Usage

```bash
python3 shellbudy.py
```

* Enter tasks or problems as text.
* ShellBuddy will suggest the next command(s) in a `bash` code block.
* You can choose to execute all, skip, or select specific commands.
* The AI will use command outputs to guide further steps.
* Type `exit` to quit.

### Example:

````
You: Find the file example.txt
ShellBuddy suggests:
```bash
find / -name 'example.txt' 2>/dev/null
````

Choice: y
[Executes command, returns output]

````

---

## Configuration (`config.json`)

```json
{
    "api_provider": "gemini",
    "model": "gemini-2.5-flash",
    "log_dir": "logs",
    "api_keys": {
        "GEMINI_API_KEY": "your_api_key_here",
        "OPENAI_API_KEY": "your_openai_api_key_here"
    }
}
````

* `api_provider`: `gemini` or `openai`
* `model`: Name of the AI model.
* `log_dir`: Directory to store logs.
* `api_keys`: Optional, keys can also be provided as environment variables.

---

## License

ShellBuddy is licensed under **MIT**. You are free to use, modify, and share it.

---

## Contributions

Contributions are welcome! Please open an issue or submit a pull request with improvements, bug fixes, or feature requests.
