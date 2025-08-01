import sqlite3
import requests
from datetime import datetime
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog

# 🔐 Replace with your actual Firebase values:
FIREBASE_PROJECT_ID = "futurepointproject"
FIREBASE_API_KEY = "AIzaSyByvsaiGZclQYfzE7XgM2rEYR9spDUNAZY"

class MainScreen(Screen):
    pass

class SearchScreen(Screen):
    pass

class FuturePointSubmitApp(MDApp):
    def build(self):
        self.init_db()
        self.sm = ScreenManager()
        self.main_screen = MainScreen(name='main')
        self.search_screen = SearchScreen(name='search')

        self.build_main_screen()
        self.build_search_screen()

        self.sm.add_widget(self.main_screen)
        self.sm.add_widget(self.search_screen)

        return self.sm

    def init_db(self):
        self.conn = sqlite3.connect("futurepoint.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, father TEXT, mobile TEXT, session TEXT, semester TEXT,
                total_fees INTEGER, paid_fees INTEGER,
                consultant TEXT, slipname TEXT, created_at TEXT
            )
        ''')
        self.conn.commit()

    def build_main_screen(self):
        layout = MDBoxLayout(orientation='vertical', padding=20, spacing=10)

        self.fields = {
            'name': MDTextField(hint_text="Student Name", required=True),
            'father': MDTextField(hint_text="Father's Name", required=True),
            'mobile': MDTextField(hint_text="Mobile Number", input_filter="int"),
            'session': MDTextField(hint_text="Session (e.g. 2024–2025)"),
            'semester': MDTextField(hint_text="Semester"),
            'total_fees': MDTextField(hint_text="Total Fees", input_filter="int"),
            'paid_fees': MDTextField(hint_text="Paid Fees", input_filter="int"),
            'consultant': MDTextField(hint_text="Consultant Name"),
            'slipname': MDTextField(hint_text="Slip Name")
        }

        for field in self.fields.values():
            layout.add_widget(field)

        btn_box = MDBoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        submit_btn = MDRaisedButton(text="Submit", on_release=self.submit_form)
        search_btn = MDRaisedButton(text="Search", on_release=lambda x: setattr(self.sm, 'current', 'search'))
        btn_box.add_widget(submit_btn)
        btn_box.add_widget(search_btn)

        layout.add_widget(btn_box)
        self.main_screen.add_widget(layout)

    def build_search_screen(self):
        layout = MDBoxLayout(orientation='vertical', padding=10, spacing=10)

        self.search_input = MDTextField(hint_text="Search by Name", on_text_validate=self.search_students)
        back_btn = MDRaisedButton(text="← Back", on_release=lambda x: setattr(self.sm, 'current', 'main'))

        self.results_box = MDBoxLayout(orientation='vertical', size_hint_y=None)
        self.results_box.bind(minimum_height=self.results_box.setter('height'))

        scroll = ScrollView()
        scroll.add_widget(self.results_box)

        layout.add_widget(back_btn)
        layout.add_widget(self.search_input)
        layout.add_widget(scroll)
        self.search_screen.add_widget(layout)

    def submit_form(self, obj):
        values = {key: field.text.strip() for key, field in self.fields.items()}
        if not values['name'] or not values['father']:
            self.show_dialog("Please enter Student Name and Father's Name")
            return

        created_at = datetime.now().strftime("%d-%m-%Y")
        self.cursor.execute('''
            INSERT INTO students (name, father, mobile, session, semester, total_fees,
                                  paid_fees, consultant, slipname, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            values['name'], values['father'], values['mobile'], values['session'], values['semester'],
            int(values['total_fees'] or 0), int(values['paid_fees'] or 0),
            values['consultant'], values['slipname'], created_at
        ))
        self.conn.commit()

        self.upload_to_firestore({**values, "created_at": created_at})
        self.show_dialog("Data saved locally and uploaded!")

        for field in self.fields.values():
            field.text = ""

    def upload_to_firestore(self, data):
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/submissions?key={FIREBASE_API_KEY}"

        # Format for Firestore API
        doc = {"fields": {}}
        for key, value in data.items():
            doc["fields"][key] = {"stringValue": str(value)}

        try:
            response = requests.post(url, json=doc)
            if not response.ok:
                print("Upload failed:", response.text)
        except Exception as e:
            print("Upload error:", e)

    def search_students(self, *args):
        query = self.search_input.text.lower().strip()
        self.results_box.clear_widgets()
        self.cursor.execute("SELECT * FROM students WHERE LOWER(name) LIKE ?", (f"%{query}%",))
        results = self.cursor.fetchall()
        if not results:
            self.results_box.add_widget(MDLabel(text="No results."))
            return

        for student in results:
            card = MDCard(orientation='vertical', padding=10, size_hint_y=None, height=180)
            card.add_widget(MDLabel(text=f"Name: {student[1]}"))
            card.add_widget(MDLabel(text=f"Father: {student[2]}"))
            card.add_widget(MDLabel(text=f"Mobile: {student[3]}"))
            card.add_widget(MDLabel(text=f"Session: {student[4]}, Semester: {student[5]}"))
            card.add_widget(MDLabel(text=f"Fees: ₹{student[6]} | Paid: ₹{student[7]}"))
            card.add_widget(MDLabel(text=f"Consultant: {student[8]}"))
            card.add_widget(MDLabel(text=f"Slip: {student[9]} | Date: {student[10]}"))
            self.results_box.add_widget(card)

    def show_dialog(self, msg):
        if hasattr(self, 'dialog') and self.dialog:
            self.dialog.dismiss()
        self.dialog = MDDialog(title="Future Point", text=msg)
        self.dialog.open()

    def on_stop(self):
        self.conn.close()

if __name__ == '__main__':
    FuturePointSubmitApp().run()
