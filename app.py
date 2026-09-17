from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import ast
import operator
from datetime import datetime
import gradio as gr
import secrets
import string

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "openai/gpt-oss-20b"
NOTES_FILE = "notes.json"
TODO_FILE = "todos.json"
MAX_HISTORY = 12
MAX_TOOL_ROUNDS = 5

# =========================
# ابزارهای کمکی
# =========================

def load_json(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except:
        pass
    return []

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("خطا در ذخیره:", e)
        return False

def get_next_id(items):
    if not items:
        return 1
    ids = []
    for item in items:
        try:
            ids.append(int(item.get("id", 0)))
        except:
            pass
    return max(ids, default=0) + 1

# =========================
# ساعت
# =========================

def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =========================
# ماشین حساب امن
# =========================

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.FloorDiv: operator.floordiv,
}

def safe_calculate(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("مقدار نامعتبر")

    if isinstance(node, ast.UnaryOp):
        op = ALLOWED_OPERATORS.get(type(node.op))
        if not op:
            raise ValueError("عملگر غیرمجاز")
        return op(safe_calculate(node.operand))

    if isinstance(node, ast.BinOp):
        op = ALLOWED_OPERATORS.get(type(node.op))
        if not op:
            raise ValueError("عملگر غیرمجاز")
        return op(safe_calculate(node.left), safe_calculate(node.right))

    raise ValueError("فقط عملیات ریاضی ساده مجاز است")

def calculator(expression):
    try:
        expression = expression.strip()
        if not expression:
            return "عبارت خالی است."
        if len(expression) > 200:
            return "عبارت خیلی طولانی است."

        tree = ast.parse(expression, mode="eval")
        result = safe_calculate(tree.body)
        return str(result)
    except ZeroDivisionError:
        return "تقسیم بر صفر مجاز نیست."
    except Exception as e:
        return f"خطا در محاسبه: {str(e)}"

# =========================
# یادداشت
# =========================

def add_note(text):
    text = str(text).strip()
    if not text:
        return "متن یادداشت خالی است."

    notes = load_json(NOTES_FILE)
    notes.append({
        "id": get_next_id(notes),
        "text": text,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    if save_json(NOTES_FILE, notes):
        return f"یادداشت ذخیره شد: {text}"
    return "خطا در ذخیره یادداشت."

def list_notes():
    notes = load_json(NOTES_FILE)
    if not notes:
        return "هیچ یادداشتی وجود ندارد."

    result = "یادداشت‌های شما:\n\n"
    for note in notes:
        result += f"{note.get('id')}. {note.get('text')} ({note.get('time')})\n"
    return result

def clear_notes():
    if save_json(NOTES_FILE, []):
        return "همه یادداشت‌ها پاک شدند."
    return "خطا در پاک کردن یادداشت‌ها."

# =========================
# لیست کارها
# =========================

def add_todo(task):
    task = str(task).strip()
    if not task:
        return "متن کار خالی است."
    todos = load_json(TODO_FILE)
    todos.append({
        "id": get_next_id(todos),
        "task": task,
        "done": False,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    if save_json(TODO_FILE, todos):
        return f"کار اضافه شد: {task}"
    return "خطا در ذخیره کار."

def list_todos():
    todos = load_json(TODO_FILE)
    if not todos:
        return "هیچ کاری در لیست نیست."

    result = "لیست کارهای شما:\n\n"
    for todo in todos:
        status = "✅" if todo.get("done") else "⬜"
        result += f"{todo.get('id')}. {status} {todo.get('task')}\n"
    return result

def complete_todo(task_id):
    try:
        task_id = int(task_id)
    except:
        return "شماره کار نامعتبر است."

    todos = load_json(TODO_FILE)
    for todo in todos:
        if todo.get("id") == task_id:
            if todo.get("done"):
                return f"کار شماره {task_id} قبلاً انجام شده."
            todo["done"] = True
            if save_json(TODO_FILE, todos):
                return f"کار شماره {task_id} انجام شد: {todo.get('task')}"
            return "خطا در ذخیره."
    return f"کار با شماره {task_id} پیدا نشد."

def clear_todos():
    if save_json(TODO_FILE, []):
        return "همه کارها پاک شدند."
    return "خطا در پاک کردن کارها."

# =========================
# خواندن فایل
# =========================

def read_text_file(file_path):
    try:
        file_path = os.path.basename(str(file_path).strip())
        if not file_path.endswith(".txt"):
            return "فقط فایل‌های .txt پشتیبانی می‌شوند."
        if not os.path.exists(file_path):
            return f"فایل «{file_path}» پیدا نشد."

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            return "فایل خالی است."
        if len(content) > 3000:
            return content[:3000] + "\n\n... (ادامه فایل نمایش داده نشد)"
        return content
    except Exception as e:
        return f"خطا در خواندن فایل: {str(e)}"

# =========================
# خلاصه‌سازی
# =========================

def summarize_text(text):
    try:
        text = str(text).strip()
        if len(text) < 50:
            return "متن خیلی کوتاه است."

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "متن را به فارسی، کوتاه و مفید خلاصه کن. فقط خلاصه را بنویس."
                },
                {"role": "user", "content": text[:4000]}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content or "خلاصه‌ای تولید نشد."
    except Exception as e:
        return f"خطا در خلاصه‌سازی: {str(e)}"

# =========================
# تبدیل واحد
# =========================

def convert_unit(value, from_unit, to_unit):
    try:
        value = float(value)
        from_unit = str(from_unit).lower().strip()
        to_unit = str(to_unit).lower().strip()

        aliases = {
            "c": "celsius", "°c": "celsius", "سانتیگراد": "celsius", "سلسیوس": "celsius",
            "f": "fahrenheit", "°f": "fahrenheit", "فارنهایت": "fahrenheit",
            "m": "meter", "متر": "meter",
            "km": "kilometer", "کیلومتر": "kilometer",
            "cm": "centimeter", "سانتی‌متر": "centimeter", "سانتیمتر": "centimeter",
            "kg": "kilogram", "کیلوگرم": "kilogram", "کیلو": "kilogram",
            "g": "gram", "گرم": "gram",
            "lb": "pound", "پوند": "pound",
            "mile": "mile", "مایل": "mile"
        }

        from_unit = aliases.get(from_unit, from_unit)
        to_unit = aliases.get(to_unit, to_unit)

        # دما
        if from_unit in ["celsius", "fahrenheit"] and to_unit in ["celsius", "fahrenheit"]:
            celsius = value if from_unit == "celsius" else (value - 32) * 5 / 9
            result = celsius if to_unit == "celsius" else celsius * 9 / 5 + 32
            return f"{value} {from_unit} = {round(result, 2)} {to_unit}"
        # طول
        length = {"meter": 1, "kilometer": 1000, "centimeter": 0.01, "mile": 1609.34}
        if from_unit in length and to_unit in length:
            result = value * length[from_unit] / length[to_unit]
            return f"{value} {from_unit} = {round(result, 4)} {to_unit}"

        # وزن
        weight = {"gram": 1, "kilogram": 1000, "pound": 453.592}
        if from_unit in weight and to_unit in weight:
            result = value * weight[from_unit] / weight[to_unit]
            return f"{value} {from_unit} = {round(result, 4)} {to_unit}"

        return f"تبدیل از {from_unit} به {to_unit} پشتیبانی نمی‌شود."
    except Exception as e:
        return f"خطا در تبدیل واحد: {str(e)}"
# =========================
# تولیدرمز
# =========================

def generate_password(length=12, use_symbols=True):
    try:
        length = int(length)
        if length < 4:
            return "طول رمز باید حداقل ۴ باشد."
        if length > 64:
            return "طول رمز نباید بیشتر از ۶۴ باشد."

        letters = string.ascii_letters
        digits = string.digits
        symbols = "!@#$%^&*()-_=+[]{}"

        alphabet = letters + digits
        if use_symbols:
            alphabet += symbols

        # حداقل یکی از هر نوع مهم
        password_chars = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
        ]

        if use_symbols:
            password_chars.append(secrets.choice(symbols))

        while len(password_chars) < length:
            password_chars.append(secrets.choice(alphabet))

        # بهم ریختن تصادفی
        secrets.SystemRandom().shuffle(password_chars)
        password = "".join(password_chars)

        return f"رمز تولید شده: {password}"
    except Exception as e:
        return f"خطا در تولید رمز: {str(e)}"
    
# =========================
# تعریف ابزارها
# =========================

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "تاریخ و ساعت فعلی را برمی‌گرداند",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "عبارت ریاضی را محاسبه می‌کند",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "مثل 25*4+10"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "یادداشت جدید ذخیره می‌کند",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "متن یادداشت"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "لیست یادداشت‌ها را نشان می‌دهد",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_notes",
            "description": "همه یادداشت‌ها را پاک می‌کند",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "کار جدید اضافه می‌کند",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "متن کار"}
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_todos",
            "description": "لیست کارها را نشان می‌دهد",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todo",
            "description": "کار را انجام‌شده می‌کند",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "شماره کار"}
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_todos",
            "description": "همه کارها را پاک می‌کند",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_text_file",
            "description": "فایل متنی را می‌خواند",
            "parameters": {"type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "مثل test.txt"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_text",
            "description": "متن را خلاصه می‌کند",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "متن برای خلاصه"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_unit",
            "description": "تبدیل واحد دما، طول و وزن",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "مقدار"},
                    "from_unit": {"type": "string", "description": "واحد مبدأ"},
                    "to_unit": {"type": "string", "description": "واحد مقصد"}
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "generate_password",
        "description": "یک رمز عبور امن تولید می‌کند",
        "parameters": {
            "type": "object",
            "properties": {
                "length": {
                    "type": "integer",
                    "description": "طول رمز، پیش‌فرض ۱۲"
                },
                "use_symbols": {
                    "type": "boolean",
                    "description": "آیا از نمادها استفاده شود؟ پیش‌فرض true"}
                },
                "required": []
            }
        }
    }
]

# =========================
# اجرای ابزار
# =========================

def execute_tool(tool_name, args):
    try:
        if tool_name == "get_current_time":
            return get_current_time()
        elif tool_name == "calculator":
            return calculator(args.get("expression", ""))
        elif tool_name == "add_note":
            return add_note(args.get("text", ""))
        elif tool_name == "list_notes":
            return list_notes()
        elif tool_name == "clear_notes":
            return clear_notes()
        elif tool_name == "add_todo":
            return add_todo(args.get("task", ""))
        elif tool_name == "list_todos":
            return list_todos()
        elif tool_name == "complete_todo":
            return complete_todo(args.get("task_id", 0))
        elif tool_name == "clear_todos":
            return clear_todos()
        elif tool_name == "read_text_file":
            return read_text_file(args.get("file_path", ""))
        elif tool_name == "summarize_text":
            return summarize_text(args.get("text", ""))
        elif tool_name == "convert_unit":
            return convert_unit(
                args.get("value", 0),
                args.get("from_unit", ""),
                args.get("to_unit", ""))
        elif tool_name == "generate_password":
            return generate_password(
            args.get("length", 12),
            args.get("use_symbols", True))
        
        else:
            return f"ابزار ناشناخته: {tool_name}"
    except Exception as e:
        return f"خطا در ابزار {tool_name}: {str(e)}"

# =========================
# History
# =========================

def normalize_history(history):
    if not history:
        return []

    normalized = []
    for item in history:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            if item[0]:
                normalized.append({"role": "user", "content": str(item[0])})
            if item[1]:
                normalized.append({"role": "assistant", "content": str(item[1])})
        elif isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role in ["user", "assistant"] and content:
                normalized.append({"role": role, "content": str(content)})
    return normalized

# =========================
# پرامپت
# =========================

system_prompt = """
تو نکسوس هستی، یک دستیار شخصی هوشمند.

شخصیت:
- دوستانه و خودمونی
- گاهی شوخ‌طبع
- در موضوعات جدی رسمی و دقیق

قواعد:
- فارسی طبیعی حرف بزن
- جواب‌ها کوتاه و مفید باشند
- اگر ابزاری لازم است از آن استفاده کن
- اطلاعات جعلی نساز
- برای محاسبه از calculator استفاده کن
- برای ساعت از get_current_time استفاده کن
- برای یادداشت و کارها از ابزارهای مربوطه استفاده کن
- برای فایل از read_text_file استفاده کن
- برای خلاصه از summarize_text استفاده کن
- برای تبدیل واحد از convert_unit استفاده کن
- برای تولید رمز عبور از generate_password استفاده کن.
"""

# =========================
# هسته اصلی
# =========================
def chat_with_nexus(message, history):
    try:
        message = str(message).strip()
        if not message:
            return "لطفاً یک پیام بنویس."

        messages = [{"role": "system", "content": system_prompt}]

        recent = normalize_history(history)[-MAX_HISTORY:]
        messages.extend(recent)
        messages.append({"role": "user", "content": message})

        for _ in range(MAX_TOOL_ROUNDS):
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.5
            )

            result = response.choices[0].message

            if not result.tool_calls:
                return result.content or "جوابی تولید نشد."

            messages.append(result)

            for tool_call in result.tool_calls:
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except:
                    args = {}

                tool_result = execute_tool(tool_call.function.name, args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(tool_result)
                })

        return "تعداد مراحل ابزار بیش از حد شد."

    except Exception as e:
        print("ERROR:", e)
        return f"یک خطا رخ داد: {str(e)}"

# =========================
# رابط کاربری
# =========================

demo = gr.ChatInterface(
    fn=chat_with_nexus,
    title="نکسوس 🤖",
    description="دستیار شخصی هوشمند تو | یادداشت، کارها، محاسبه، فایل، خلاصه، تبدیل واحد و رمز عبور",
    examples=[
        "ساعت چند است؟",
        "۲۵۰ تقسیم بر ۵ چی میشه؟",
        "اینو یادداشت کن: فردا ساعت ۱۰ جلسه دارم",
        "لیست کارهام چیه؟",
        "یک رمز عبور ۱۶ کاراکتری بساز",
        "۲۵ درجه سانتی‌گراد چند فارنهایته؟",
        "خودت رو معرفی کن"
    ],
    cache_examples=False
)

if __name__ == "__main__":
    demo.launch(
        share=False,
        inbrowser=True
    )