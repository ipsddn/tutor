import sys
import os
import time
import threading
import datetime
import subprocess

import speech_recognition as sr
import pyttsx3
import google.generativeai as genai

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QPixmap, QPainter, QPen, QColor

from playwright.sync_api import sync_playwright

# ==========================================
# CREDENTIALS & CONFIGURATION
# ==========================================
# Integrated Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6IbYVtCgT0b8Ls-IBd0_uqk_hxFx8wqKZ6PQlsGHRs2JQ")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction="You are MAX, an intelligent AI Assistant created by Sumit Sharma. Keep your answers concise, helpful, friendly, and short (1-2 lines maximum) so they sound natural when spoken out loud. Answer in Hindi or Hinglish when appropriate."
        )
    except Exception as e:
        print(f"Gemini Init Error: {e}")
        model = None
else:
    model = None

NVR_USERNAME = "admin"
NVR_PASSWORD = "IPS@12345"
NVR_URL = "https://10.1.1.198/doc/index.html#/portal/login"
ERP_URL = "https://ipserp.edunexttechnologies.com/"
MOD_URL = "http://103.230.155.58:90/mod/admin_panel.php"

# Time Configuration for Idle Check (Seconds)
IDLE_CHECK_INTERVAL = 120

last_interaction_time = time.time()
speech_lock = threading.Lock()

def update_last_activity():
    """System activity timestamp update karta hai"""
    global last_interaction_time
    last_interaction_time = time.time()

def open_in_chrome(url):
    """Direct Google Chrome Executable me URL open karein"""
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    ]
    
    launched = False
    for path in chrome_paths:
        if os.path.exists(path):
            try:
                subprocess.Popen([path, url])
                launched = True
                break
            except Exception as e:
                print(f"Failed launching {path}: {e}")
    
    if not launched:
        import webbrowser
        webbrowser.open(url)

def handle_nvr_playwright_login():
    """Recorded Playwright Sequence with Window Split & Layout"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--start-maximized"])
            context = browser.new_context(ignore_https_errors=True, no_viewport=True)
            page = context.new_page()

            page.goto(NVR_URL, wait_until="networkidle")
            
            user_field = page.get_by_role("textbox", name="User Name")
            user_field.click()
            user_field.fill(NVR_USERNAME)
            user_field.press("Tab")

            pass_field = page.get_by_role("textbox", name="Password")
            pass_field.fill(NVR_PASSWORD)

            page.get_by_role("button", name="Log In").click()
            page.wait_for_timeout(3000)
            
            try:
                page.get_by_title("Window Split").click()
                page.get_by_title("2x2").click()
                page.locator("div:nth-child(2) > .ch > .ch-btn-left > .path3").click()
            except Exception as layout_err:
                print(f"Layout Selection Warning: {layout_err}")

            page.wait_for_timeout(15000)

    except Exception as e:
        print(f"Playwright NVR Login Error: {e}")

# ==========================================
# 1. VOICE & SPEECH ENGINE SETUP
# ==========================================
def speak(text):
    """Thread-safe voice output function"""
    with speech_lock:
        print(f"MAX: {text}")
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 165)
            engine.setProperty('volume', 1.0)
            
            voices = engine.getProperty('voices')
            if len(voices) > 1:
                engine.setProperty('voice', voices[1].id)
            
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"Speech Engine Error: {e}")

def wish_user():
    """Time-based greeting"""
    hour = datetime.datetime.now().hour
    if 4 <= hour < 12:
        return "Good Morning Sir! Aapka din shubh aur productive ho!"
    elif 12 <= hour < 17:
        return "Good Afternoon Sir! How can I help you?"
    elif 17 <= hour < 22:
        return "Good Evening Sir! Batayein, main aapki kya help kar sakta hoon?"
    else:
        return "Good Night Sir! Have a wonderful night!"

def listen_command():
    """Microphone voice input processing"""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.8)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=6)
            command = recognizer.recognize_google(audio, language="en-IN")
            print(f"You said: {command}")
            update_last_activity()
            return command.lower()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return ""
        except Exception as e:
            print(f"Listening Error: {e}")
            return ""

def ask_gemini_ai(prompt):
    """Generates intelligent response using Gemini LLM"""
    if not model:
        return "Sir, Gemini AI model initialize nahi ho paaya."
    try:
        response = model.generate_content(prompt)
        return response.text.replace("*", "").strip()
    except Exception as e:
        print(f"Gemini AI Error: {e}")
        return "Sorry Sir, AI response process karne me issue aa raha hai."

# ==========================================
# 2. VOICE COMMAND EXECUTION (HYBRID ENGINE)
# ==========================================
def process_command(command, status_callback):
    if not command:
        return

    status_callback(f"Command: {command}")

    # SYSTEM CONTROL COMMANDS
    if any(q in command for q in ["exit", "shutdown", "stop", "bye", "goodbye"]):
        speak("Shutting down MAX. Have a great day, Sir!")
        os._exit(0)

    # LOCAL APPLICATION & PORTAL LAUNCHERS
    elif any(q in command for q in ["open google", "chrome open", "google open"]):
        open_in_chrome("https://www.google.com")
        speak("Google Chrome open kar diya hai sir.")
    elif "open youtube" in command or "youtube open" in command:
        open_in_chrome("https://www.youtube.com")
        speak("YouTube open kar diya hai sir.")
    elif any(q in command for q in ["open erp", "erp open", "edunext"]):
        open_in_chrome(ERP_URL)
        speak("ERP portal open kar diya hai sir.")
    elif any(q in command for q in ["open mod", "mod open", "master on duty"]):
        open_in_chrome(MOD_URL)
        speak("Master on Duty panel open kar diya hai sir.")
    elif any(q in command for q in ["open ms word", "open word", "word open"]):
        try:
            os.system("start winword")
            speak("Microsoft Word open kar diya hai sir.")
        except Exception:
            speak("MS Word open karne me error aaya sir.")
    elif "open excel" in command or "excel open" in command:
        try:
            os.system("start excel")
            speak("Microsoft Excel open kar diya hai sir.")
        except Exception:
            speak("MS Excel open karne me error aaya sir.")
    elif any(q in command for q in ["open whatsapp", "whatsapp open"]):
        open_in_chrome("https://web.whatsapp.com")
        speak("WhatsApp Web open kar diya hai sir.")
    elif "open nvr" in command or "nvr ip" in command:
        status_callback("Opening NVR Portal via Playwright...")
        threading.Thread(target=handle_nvr_playwright_login, daemon=True).start()
        speak("NVR portal open karke login process start kar di hai sir.")
    elif "notepad" in command:
        os.system("notepad")
        speak("Notepad open kar diya hai sir.")
    elif "close window" in command or "close chrome" in command:
        try:
            import pyautogui
            pyautogui.hotkey('alt', 'f4')
            speak("Active window close kar di hai sir.")
        except ImportError:
            speak("PyAutoGUI package install nahi hai sir.")

    # REAL AI INTELLIGENCE FOR EVERYTHING ELSE
    else:
        status_callback("Thinking (AI Response)...")
        ai_reply = ask_gemini_ai(command)
        speak(ai_reply)

# ==========================================
# 3. ROTATING BORDER DISPLAY WIDGET
# ==========================================
class RotatingFaceWidget(QLabel):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 300)
        self.angle = 0
        self.image_path = image_path
        
        if os.path.exists(self.image_path):
            self.original_pixmap = QPixmap(self.image_path)
        else:
            self.original_pixmap = None

        self.rotate_timer = QTimer(self)
        self.rotate_timer.timeout.connect(self.update_rotation)
        self.rotate_timer.start(30)

    def update_rotation(self):
        self.angle = (self.angle + 3) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x, center_y = self.width() // 2, self.height() // 2
        radius = 140

        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            px = center_x - scaled_pixmap.width() // 2
            py = center_y - scaled_pixmap.height() // 2
            painter.drawPixmap(px, py, scaled_pixmap)
        else:
            painter.setPen(QPen(QColor("#FF9100"), 2))
            painter.drawText(self.rect(), Qt.AlignCenter, "MAX FACE IMAGE MISSING")

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.angle)

        pen_glow = QPen(QColor("#FF9100"), 4, Qt.SolidLine)
        painter.setPen(pen_glow)
        painter.drawArc(-radius, -radius, radius * 2, radius * 2, 0 * 16, 80 * 16)
        painter.drawArc(-radius, -radius, radius * 2, radius * 2, 120 * 16, 80 * 16)
        painter.drawArc(-radius, -radius, radius * 2, radius * 2, 240 * 16, 80 * 16)

        pen_thin = QPen(QColor("#FFAB40"), 1, Qt.DashLine)
        painter.setPen(pen_thin)
        painter.drawEllipse(-radius + 6, -radius + 6, (radius - 6) * 2, (radius - 6) * 2)

        painter.restore()

# ==========================================
# 4. MAX GUI INTERFACE & SIGNALS
# ==========================================
class UIBridge(QObject):
    status_signal = pyqtSignal(str)

class MaxUI(QWidget):
    def __init__(self):
        super().__init__()
        self.old_pos = None
        self.bridge = UIBridge()
        self.bridge.status_signal.connect(self.set_status_text)
        
        self.initUI()
        self.listening = True
        
        self.bg_thread = threading.Thread(target=self.voice_loop, daemon=True)
        self.bg_thread.start()

        self.idle_thread = threading.Thread(target=self.idle_availability_checker, daemon=True)
        self.idle_thread.start()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(360, 480)
        self.move(100, 80)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel("M.A.X. AI", self)
        self.title_label.setFont(QFont("Consolas", 22, QFont.Bold))
        self.title_label.setStyleSheet("color: #FF9100; text-align: center; margin-bottom: 5px;")
        self.title_label.setAlignment(Qt.AlignCenter)

        image_path = r"C:\Users\shaurya\Desktop\jarvis\JARVIS Face Image.jpg"
        self.face_widget = RotatingFaceWidget(image_path, self)

        self.status_label = QLabel("SYSTEM ONLINE\nListening for commands...", self)
        self.status_label.setFont(QFont("Consolas", 10, QFont.Bold))
        self.status_label.setStyleSheet("""
            color: #FFAB40;
            border: 1px solid #FF9100;
            padding: 10px;
            background-color: rgba(10, 20, 35, 0.9);
            border-radius: 8px;
            margin-top: 10px;
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.face_widget)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None and event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def update_status(self, text):
        self.bridge.status_signal.emit(text)

    def set_status_text(self, text):
        self.status_label.setText(text)

    def voice_loop(self):
        initial_wish = wish_user()
        speak(f"{initial_wish} Max AI core online and ready.")
        update_last_activity()
        while self.listening:
            self.update_status("Listening...")
            cmd = listen_command()
            if cmd:
                self.update_status(f"Processing:\n'{cmd}'")
                process_command(cmd, self.update_status)

    def idle_availability_checker(self):
        """Idle rehne par periodic voice alert deta hai"""
        while self.listening:
            time.sleep(10)
            elapsed = time.time() - last_interaction_time
            if elapsed >= IDLE_CHECK_INTERVAL:
                speak("Sir, main online hu aur aapki help ke liye ready hu.")
                update_last_activity()

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = MaxUI()
    gui.show()
    sys.exit(app.exec_())