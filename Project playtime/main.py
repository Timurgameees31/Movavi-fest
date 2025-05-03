import telebot
from telebot import types
import sqlite3
import time

Token = '7547849192:AAGQafZV9WP05FBSnsTiE4QIwoqnoEhKcl8' 
bot = telebot.TeleBot(Token)

teacher_code = "nebulabrasque721"

# Подключаемся к базе данных
conn = sqlite3.connect('users.db', timeout=10)
c = conn.cursor()

# Создаем таблицу для заданий, если ее нет
c.execute('''CREATE TABLE IF NOT EXISTS tasks
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              student_id INTEGER,
              teacher_id INTEGER,
              task_text TEXT,
              answer_text TEXT,
              points INTEGER DEFAULT 10,
              status TEXT DEFAULT 'pending',
              timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()
conn.close()

# Инлайн-клавиатуры
keyboard = types.InlineKeyboardMarkup()
button_link_inline = types.InlineKeyboardButton('FAQ', url='https://Timurgameees31.github.io/faq-page/')
button_inline = types.InlineKeyboardButton("Зарегистрироваться / Войти", callback_data="registration")
button_rating_inline = types.InlineKeyboardButton("Рейтинг пользователей", callback_data="rating")
button_quest_inline = types.InlineKeyboardButton("Получить задание", callback_data="quest")
button_quest_give_inline = types.InlineKeyboardButton("Выдать задание", callback_data="quest_give")
button_profile_inline = types.InlineKeyboardButton("Профиль", callback_data="profile")
button_teacher_inline = types.InlineKeyboardButton("Зарегистрироваться / Войти учителю", callback_data="teacher")
button_logout_inline = types.InlineKeyboardButton("Выход", callback_data="logout")
keyboard.add(button_link_inline, button_inline, button_rating_inline, button_quest_inline, button_teacher_inline, button_profile_inline)

student_reply_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
student_reply_keyboard.add(
    types.KeyboardButton("FAQ"),
    types.KeyboardButton("Рейтинг пользователей"),
    types.KeyboardButton("Получить задание"),
    types.KeyboardButton("Профиль"),
    types.KeyboardButton("Выход")
)

teacher_reply_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
teacher_reply_keyboard.add(
    types.KeyboardButton("FAQ"),
    types.KeyboardButton("Рейтинг пользователей"),
    types.KeyboardButton("Выдать задание"),
    types.KeyboardButton("Профиль"),
    types.KeyboardButton("Проверить задания"),
    types.KeyboardButton("Выход")
)

# Словарь для хранения состояний пользователей
USER_STATE = {}
TASK_STATE = {}

def create_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Проверка, существует ли таблица users
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    table_exists = c.fetchone()
    
    if not table_exists:
        c.execute('''CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tg_id INTEGER,
                        first_name TEXT NOT NULL,
                        last_name TEXT NOT NULL,
                        username TEXT,
                        password TEXT NOT NULL,
                        school_class TEXT,
                        points INTEGER DEFAULT 0,
                        role TEXT DEFAULT 'student',
                        is_active INTEGER DEFAULT 1
                    )''')
    else:
        # Проверка существующих колонок в users
        c.execute("PRAGMA table_info(users)")
        existing_columns = {column[1] for column in c.fetchall()}
        
        required_columns = {
            "tg_id": "INTEGER UNIQUE",
            "first_name": "TEXT",
            "last_name": "TEXT",
            "username": "TEXT",
            "password": "TEXT",
            "school_class": "TEXT",
            "points": "INTEGER DEFAULT 0",
            "role": "TEXT DEFAULT 'student'",
            "is_active": "INTEGER DEFAULT 1"
        }

        for column, col_type in required_columns.items():
            if column not in existing_columns:
                c.execute(f"ALTER TABLE users ADD COLUMN {column} {col_type}")
    
    # Проверка и создание/обновление таблицы tasks
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
    tasks_table_exists = c.fetchone()
    
    if not tasks_table_exists:
        c.execute('''CREATE TABLE tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER,
                        teacher_id INTEGER,
                        task_text TEXT,
                        answer_text TEXT,
                        points INTEGER DEFAULT 10,
                        status TEXT DEFAULT 'pending',
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')
    else:
        # Проверка существующих колонок в tasks
        c.execute("PRAGMA table_info(tasks)")
        existing_columns = {column[1] for column in c.fetchall()}
        
        required_columns = {
            "student_id": "INTEGER",
            "teacher_id": "INTEGER",
            "task_text": "TEXT",
            "answer_text": "TEXT",
            "points": "INTEGER DEFAULT 10",
            "status": "TEXT DEFAULT 'pending'",
            "timestamp": "DATETIME DEFAULT CURRENT_TIMESTAMP"
        }

        for column, col_type in required_columns.items():
            if column not in existing_columns:
                try:
                    c.execute(f"ALTER TABLE tasks ADD COLUMN {column} {col_type}")
                except sqlite3.OperationalError as e:
                    print(f"Ошибка при добавлении колонки {column}: {e}")

    c.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(tg_id, is_active)")
    conn.commit()
    conn.close()

def register_user(first_name, last_name, username=None, school_class=None, role='student', user_id=None, password=None):
    if not password:
        print("Пароль не передан — регистрация невозможна.")
        return

    try:
        with sqlite3.connect('users.db', timeout=10) as conn:
            c = conn.cursor()
            
            # Проверяем, существует ли пользователь с таким tg_id
            c.execute("SELECT * FROM users WHERE tg_id=?", (user_id,))
            existing_user = c.fetchone()
            
            if existing_user:
                # Если пользователь существует, обновляем его данные
                c.execute("""UPDATE users SET 
                            first_name=?, 
                            last_name=?, 
                            username=?, 
                            school_class=?, 
                            role=?, 
                            password=?, 
                            is_active=1 
                            WHERE tg_id=?""",
                         (first_name, last_name, username, school_class, role, password, user_id))
            else:
                # Если пользователя нет, создаем нового
                c.execute("""INSERT INTO users 
                           (tg_id, first_name, last_name, username, school_class, points, role, password, is_active)
                           VALUES (?, ?, ?, ?, ?, 0, ?, ?, 1)""",
                        (user_id, first_name, last_name, username, school_class, role, password))
            
            conn.commit()
    except sqlite3.OperationalError as e:
        print(f"Ошибка SQLite: {e}")
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.chat.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE tg_id=?", (user_id,))
    user = c.fetchone()
    conn.close()

    if user:
        role = user[0]
        if role == 'teacher':
            user_keyboard = types.InlineKeyboardMarkup()
            user_keyboard.add(button_link_inline, button_rating_inline, button_quest_give_inline, button_profile_inline, button_logout_inline)
            bot.send_message(user_id, "Вы вошли как учитель. Вы можете давать задания ученикам.", reply_markup=user_keyboard)
            bot.send_message(user_id, "Для навигации используйте панель ниже.", reply_markup=teacher_reply_keyboard)
        else:
            user_keyboard = types.InlineKeyboardMarkup()
            user_keyboard.add(button_link_inline, button_rating_inline, button_quest_inline, button_profile_inline, button_logout_inline)
            bot.send_message(user_id, "Ты вошёл как ученик! Начинай учиться :)", reply_markup=user_keyboard)
            bot.send_message(user_id, "Для навигации используй панель ниже.", reply_markup=student_reply_keyboard)
    else:
        bot.send_message(user_id, "Привет! Для начала регистрации нажми кнопку ниже.", reply_markup=keyboard)
        bot.send_message(user_id, "Для навигации используй кнопки из панели.", reply_markup=student_reply_keyboard)
        
@bot.message_handler(func=lambda message: message.text == "Выход")
def logout_user(message):
    user_id = message.chat.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Просто деактивируем текущего пользователя (не удаляем)
    c.execute("UPDATE users SET is_active=0 WHERE tg_id=? AND is_active=1", (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(user_id, "Вы вышли из аккаунта. Для входа или регистрации нового аккаунта используйте кнопки ниже.", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "logout")
def logout_user_callback(call):
    user_id = call.message.chat.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Просто деактивируем текущего пользователя (не удаляем)
    c.execute("UPDATE users SET is_active=0 WHERE tg_id=? AND is_active=1", (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(user_id, "Вы вышли из аккаунта. Для входа или регистрации нового аккаунта используйте кнопки ниже.", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "teacher")
def teacher_registration_inline(call):
    user_id = call.message.chat.id
    USER_STATE[user_id] = {'step': 'teacher_password'}
    bot.send_message(user_id, "Введите учительский пароль:")

@bot.message_handler(func=lambda message: message.text == "Зарегистрироваться учителю")
def teacher_registration_reply(message):
    user_id = message.chat.id
    USER_STATE[user_id] = {'step': 'teacher_password'}
    bot.send_message(user_id, "Введите учительский пароль:")

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'teacher_set_password')
def teacher_set_password(message):
    user_id = message.chat.id
    password = message.text.strip()

    register_user(
        first_name="Учитель",
        last_name="-",
        username=message.from_user.username,
        user_id=user_id,
        password=password,
        role='teacher'
    )

    user_keyboard = types.InlineKeyboardMarkup()
    user_keyboard.add(button_link_inline, button_rating_inline, button_quest_give_inline, button_logout_inline)
    bot.send_message(user_id, "Вы вошли как учитель. Вы можете давать задания ученикам.", reply_markup=user_keyboard)
    bot.send_message(user_id, "Для навигации используйте панель ниже.", reply_markup=teacher_reply_keyboard)

    del USER_STATE[user_id]

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'teacher_password')
def check_teacher_password(message):
    user_id = message.chat.id
    if message.text.strip() == teacher_code:
        USER_STATE[user_id]['step'] = 'teacher_set_password'
        bot.send_message(user_id, "Учительский пароль принят. Придумайте пароль для своей учётной записи:")
    else:
        bot.send_message(user_id, "Неверный пароль. Попробуйте снова:")

@bot.callback_query_handler(func=lambda call: call.data == "quest")
@bot.message_handler(func=lambda message: message.text == "Получить задание")
def send_task(call_or_msg):
    chat_id = call_or_msg.message.chat.id if hasattr(call_or_msg, 'message') else call_or_msg.chat.id
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT task_text, id FROM tasks WHERE student_id=? AND status='pending'", (chat_id,))
    task = c.fetchone()
    conn.close()
    
    if task:
        task_text, task_id = task
        bot.send_message(chat_id, f"Ваше задание:\n{task_text}\n\nОтправьте ответ на это сообщение.")
        USER_STATE[chat_id] = {'step': 'send_answer', 'task_id': task_id}
    else:
        bot.send_message(chat_id, "У вас нет новых заданий.")

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'get_student_id')
def process_student_id(message):
    user_id = message.chat.id
    try:
        student_id = int(message.text)
        
        # Проверка, что учитель не пытается выдать задание самому себе
        if student_id == user_id:
            bot.send_message(user_id, "Вы не можете выдать задание самому себе. Введите ID ученика:")
            return
        
        # Проверяем, существует ли ученик с таким ID
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT tg_id FROM users WHERE tg_id=? AND role='student'", (student_id,))
        student_exists = c.fetchone()
        conn.close()
        
        if not student_exists:
            bot.send_message(user_id, "Ученик с таким ID не найден. Попробуйте еще раз:")
            return
            
        USER_STATE[user_id]['student_id'] = student_id
        USER_STATE[user_id]['step'] = 'get_task_text'
        bot.send_message(user_id, "Введите текст задания:")
    except ValueError:
        bot.send_message(user_id, "ID ученика должен быть числом. Попробуйте еще раз:")

def show_profile(message):
    user_id = message.chat.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    try:
        # Получаем данные текущего активного пользователя
        c.execute("""
            SELECT first_name, last_name, username, school_class, points, role 
            FROM users 
            WHERE tg_id=? AND is_active=1
            LIMIT 1
        """, (user_id,))
        user_data = c.fetchone()
        
        if not user_data:
            bot.send_message(user_id, "Профиль не найден. Пожалуйста, войдите в аккаунт.")
            return
        
        first_name, last_name, username, school_class, points, role = user_data
        
        # Обработка случая, когда username равен None
        username_display = f"@{username}" if username else "не указан"
        
        if role == 'student':
            # Формируем информацию для ученика
            profile_text = f"""
📌 *Профиль ученика*:

👤 *Имя:* {first_name} {last_name}
🔖 *Никнейм:* {username_display}
🏫 *Класс:* {school_class if school_class else 'не указан'}
🆔 *Telegram ID:* `{user_id}`

🏆 *Баллы:* {points}
"""
            # Добавляем место в параллели, если указан класс
            if school_class and len(school_class) > 1:
                try:
                    parallel = school_class[:-1]
                    c.execute("""
                        SELECT COUNT(*) + 1 
                        FROM users 
                        WHERE school_class LIKE ? || '%' 
                        AND points > ? 
                        AND role = 'student' 
                        AND is_active = 1
                    """, (parallel, points))
                    position = c.fetchone()[0]
                    
                    c.execute("""
                        SELECT COUNT(*) 
                        FROM users 
                        WHERE school_class LIKE ? || '%' 
                        AND role = 'student' 
                        AND is_active = 1
                    """, (parallel,))
                    total_in_parallel = c.fetchone()[0]
                    
                    profile_text += f"📊 *Место в параллели:* {position} из {total_in_parallel}\n"
                except Exception as e:
                    print(f"Ошибка при расчете рейтинга: {e}")
                    profile_text += "📊 *Место в параллели:* данные временно недоступны\n"
        
        else:  # Для учителя
            # Получаем статистику заданий
            c.execute("SELECT COUNT(*) FROM tasks WHERE teacher_id=?", (user_id,))
            tasks_given = c.fetchone()[0]
            
            c.execute("""
                SELECT COUNT(*) 
                FROM tasks 
                WHERE teacher_id=? 
                AND status IN ('completed_correct', 'completed_wrong')
            """, (user_id,))
            tasks_checked = c.fetchone()[0]
            
            profile_text = f"""
📌 *Профиль учителя*:

👤 *Имя:* {first_name} {last_name}
🔖 *Никнейм:* {username_display}
🆔 *Telegram ID:* `{user_id}`

📝 *Заданий выдано:* {tasks_given}
✅ *Заданий проверено:* {tasks_checked}
"""
        
        bot.send_message(user_id, profile_text, parse_mode='Markdown')
        
    except Exception as e:
        print(f"Ошибка при отображении профиля: {e}")
        bot.send_message(user_id, "Произошла ошибка при загрузке профиля. Пожалуйста, попробуйте позже.")
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data == "profile")
def profile_callback(call):
    show_profile(call.message)

# При успешном входе любого пользователя
def successful_login(user_id, role):
    if role == 'teacher':
        user_keyboard = types.InlineKeyboardMarkup()
        user_keyboard.add(button_link_inline, button_rating_inline, button_quest_give_inline, button_profile_inline, button_logout_inline)
        bot.send_message(user_id, "Вы вошли как учитель.", reply_markup=user_keyboard)
        bot.send_message(user_id, "Для навигации используйте панель ниже.", reply_markup=teacher_reply_keyboard)
    else:
        user_keyboard = types.InlineKeyboardMarkup()
        user_keyboard.add(button_link_inline, button_rating_inline, button_quest_inline, button_profile_inline, button_logout_inline)
        bot.send_message(user_id, "Вы вошли как ученик.", reply_markup=user_keyboard)
        bot.send_message(user_id, "Для навигации используй панель ниже.", reply_markup=student_reply_keyboard)
    
    # Всегда показываем профиль после входа
    bot.send_message(user_id, "Ваш профиль:")
    show_profile(types.Message(message_id=0, chat=types.Chat(id=user_id, type='private'), from_user=types.User(id=user_id, first_name='', is_bot=False), date=0, content_type='text', options={}, json_string=''))

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'login_password')
def process_login_password(message):
    user_id = message.chat.id
    password = message.text.strip()
    first_name = USER_STATE[user_id]['first_name']
    last_name = USER_STATE[user_id]['last_name']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Ищем пользователя по имени, фамилии и паролю (независимо от is_active)
    c.execute("SELECT * FROM users WHERE first_name=? AND last_name=? AND password=?", 
              (first_name, last_name, password))
    user = c.fetchone()
    conn.close()

    if user:
        # Активируем пользователя (устанавливаем is_active=1)
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET is_active=1 WHERE tg_id=?", (user[1],))  # user[1] - это tg_id
        conn.commit()
        conn.close()
        
        # Устанавливаем клавиатуру в зависимости от роли
        role = user[8]  # индекс 8 — это поле "role"
        if role == 'teacher':
            user_keyboard = types.InlineKeyboardMarkup()
            user_keyboard.add(button_link_inline, button_rating_inline, button_quest_give_inline, button_profile_inline, button_logout_inline)
            bot.send_message(user_id, f"Добро пожаловать обратно, {first_name} {last_name}!", reply_markup=user_keyboard)
            bot.send_message(user_id, "Для навигации используйте панель ниже.", reply_markup=teacher_reply_keyboard)
        else:
            user_keyboard = types.InlineKeyboardMarkup()
            user_keyboard.add(button_link_inline, button_rating_inline, button_quest_inline, button_profile_inline, button_logout_inline)
            bot.send_message(user_id, f"Добро пожаловать обратно, {first_name} {last_name}!", reply_markup=user_keyboard)
            bot.send_message(user_id, "Для навигации используй панель ниже.", reply_markup=student_reply_keyboard)
        
        # Показываем профиль
        show_profile(message)
        del USER_STATE[user_id]
    else:
        bot.send_message(user_id, "Неверный пароль. Попробуйте еще раз:")

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'set_password')
def set_password(message):
    user_id = message.chat.id
    USER_STATE[user_id]['password'] = message.text.strip()
    data = USER_STATE[user_id]

    print(f"Регистрируем пользователя: {data}")  # Отладочный вывод
    
    register_user(
        first_name=data['first_name'],
        last_name=data['last_name'],
        username=data.get('username'),
        school_class=data.get('school_class'),
        role='student',
        user_id=user_id,
        password=data['password']
    )
    
    # Проверяем, что пользователь добавился
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE tg_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        print(f"Пользователь успешно добавлен: {user}")
        bot.send_message(user_id, f"Регистрация завершена!\nИмя: {data['first_name']}\nФамилия: {data['last_name']}\nКласс: {data['school_class']}")
        successful_login(user_id, 'student')    
    else:
        print("Ошибка: пользователь не добавлен в БД")
        bot.send_message(user_id, "Произошла ошибка при регистрации. Попробуйте еще раз.")
    
    del USER_STATE[user_id]
    
@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'teacher_set_password')
def teacher_set_password(message):
    user_id = message.chat.id
    password = message.text.strip()

    register_user(
        first_name="Учитель",
        last_name="-",
        username=message.from_user.username,
        user_id=user_id,
        password=password,
        role='teacher'
    )

    successful_login(user_id, 'teacher')
    del USER_STATE[user_id]

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'send_answer')
def process_student_answer(message):
    user_id = message.chat.id
    task_id = USER_STATE[user_id]['task_id']
    answer = message.text
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET answer_text=?, status='waiting_review' WHERE id=?", (answer, task_id))
    conn.commit()
    
    # Получаем ID учителя, который выдал задание
    c.execute("SELECT teacher_id FROM tasks WHERE id=?", (task_id,))
    teacher_id = c.fetchone()[0]
    conn.close()
    
    del USER_STATE[user_id]
    bot.send_message(user_id, "Ваш ответ отправлен учителю на проверку.")
    
    # Уведомляем учителя
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Верно", callback_data=f"correct_{task_id}"),
        types.InlineKeyboardButton("Неверно", callback_data=f"wrong_{task_id}")
    )
    bot.send_message(teacher_id, f"Ученик отправил ответ на задание ID {task_id}:\n\n{answer}", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("correct_", "wrong_")))
def review_answer(call):
    task_id = int(call.data.split("_")[1])
    is_correct = call.data.startswith("correct_")
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Получаем информацию о задании
    c.execute("SELECT student_id, teacher_id FROM tasks WHERE id=?", (task_id,))
    student_id, teacher_id = c.fetchone()
    
    # Обновляем статус задания
    status = "completed_correct" if is_correct else "completed_wrong"
    c.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    
    # Если ответ верный, добавляем баллы ученику
    if is_correct:
        c.execute("UPDATE users SET points=points+10 WHERE tg_id=?", (student_id,))
    
    conn.commit()
    conn.close()
    
    # Уведомляем ученика
    result_text = "верно" if is_correct else "неверно"
    points_text = " +10 баллов" if is_correct else ""
    bot.send_message(student_id, f"Учитель проверил ваш ответ: {result_text}{points_text}")
    
    # Уведомляем учителя
    bot.send_message(teacher_id, f"Вы отметили ответ как {result_text}.")

@bot.callback_query_handler(func=lambda call: call.data == "quest_give")
@bot.message_handler(func=lambda message: message.text == "Выдать задание")
def give_task(call_or_msg):
    chat_id = call_or_msg.message.chat.id if hasattr(call_or_msg, 'message') else call_or_msg.chat.id
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("Отдельному ученику", callback_data="give_to_student"),
        types.InlineKeyboardButton("Целому классу", callback_data="give_to_class")
    )
    bot.send_message(chat_id, "Выберите, кому выдать задание:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "give_to_student")
def give_to_student(call):
    user_id = call.message.chat.id
    USER_STATE[user_id] = {'step': 'get_student_id', 'target': 'student'}
    bot.send_message(user_id, "Введите ID ученика, которому хотите выдать задание:")

@bot.callback_query_handler(func=lambda call: call.data == "give_to_class")
def give_to_class(call):
    user_id = call.message.chat.id
    USER_STATE[user_id] = {'step': 'select_class_grade', 'target': 'class'}
    send_grade_selection_for_task(user_id)

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'get_task_points')
def process_task_points(message):
    user_id = message.chat.id
    try:
        points = int(message.text)
        if points <= 0:
            raise ValueError
        
        task_text = USER_STATE[user_id]['task_text']
        teacher_id = user_id
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        if USER_STATE[user_id]['target'] == 'student':
            # Отправка одному ученику
            student_id = USER_STATE[user_id]['student_id']
            c.execute("""INSERT INTO tasks 
                        (student_id, teacher_id, task_text, points, status) 
                        VALUES (?, ?, ?, ?, 'pending')""",
                     (student_id, teacher_id, task_text, points))
            conn.commit()
            bot.send_message(user_id, f"Задание успешно отправлено ученику с ID {student_id}.")
            
            try:
                bot.send_message(student_id, "У вас новое задание от учителя! Нажмите кнопку 'Получить задание' для просмотра.")
            except Exception as e:
                bot.send_message(user_id, f"Задание сохранено, но не удалось уведомить ученика: {e}")
                
        else:
            # Отправка всему классу
            school_class = USER_STATE[user_id]['school_class']
            c.execute("SELECT tg_id FROM users WHERE school_class=? AND role='student' AND is_active=1", (school_class,))
            students = c.fetchall()
            
            if not students:
                bot.send_message(user_id, f"В классе {school_class} нет активных учеников.")
                conn.close()
                del USER_STATE[user_id]
                return
            
            count = 0
            failed_notifications = 0
            for student in students:
                try:
                    student_id = student[0]
                    c.execute("""INSERT INTO tasks 
                                (student_id, teacher_id, task_text, points, status) 
                                VALUES (?, ?, ?, ?, 'pending')""",
                             (student_id, teacher_id, task_text, points))
                    count += 1
                    
                    try:
                        bot.send_message(student_id, "У вас новое задание от учителя! Нажмите кнопку 'Получить задание' для просмотра.")
                    except:
                        failed_notifications += 1
                        
                except Exception as e:
                    print(f"Ошибка при отправке задания ученику {student_id}: {e}")
                    continue
            
            conn.commit()
            
            if failed_notifications > 0:
                bot.send_message(user_id, f"Задание отправлено {count} ученикам класса {school_class}. Не удалось уведомить {failed_notifications} учеников.")
            else:
                bot.send_message(user_id, f"Задание успешно отправлено всем {count} ученикам класса {school_class}.")
        
        conn.close()
        del USER_STATE[user_id]
        
    except ValueError:
        bot.send_message(user_id, "Количество баллов должно быть положительным числом. Попробуйте еще раз:")
    except Exception as e:
        bot.send_message(user_id, f"Произошла ошибка: {str(e)}")
        print(f"Ошибка при обработке задания: {e}")
        del USER_STATE[user_id]

def send_grade_selection_for_task(user_id):
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    buttons = [types.InlineKeyboardButton(str(grade), callback_data=f"task_grade_{grade}") for grade in range(1, 12)]
    keyboard.add(*buttons)
    bot.send_message(user_id, "Выберите класс (номер):", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("task_grade_"))
def process_task_grade_selection(call):
    user_id = call.message.chat.id
    grade = call.data.split("_")[2]
    USER_STATE[user_id]['grade'] = grade
    USER_STATE[user_id]['step'] = 'select_class_letter'
    send_letter_selection_for_task(user_id)

def send_letter_selection_for_task(user_id):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(letter, callback_data=f"task_class_{letter}") for letter in ["А", "Б", "В"]]
    keyboard.add(*buttons)
    bot.send_message(user_id, "Выберите букву класса:", reply_markup=keyboard)

def send_letter_selection_for_task(user_id):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(letter, callback_data=f"task_class_{letter}") 
               for letter in ["А", "Б", "В"]]  # Буквы классов
    keyboard.add(*buttons)
    bot.send_message(user_id, "Выберите букву класса:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("task_class_"))
def process_task_class_selection(call):
    user_id = call.message.chat.id
    letter = call.data.split("_")[2]
    school_class = f"{USER_STATE[user_id]['grade']}{letter}"
    USER_STATE[user_id]['school_class'] = school_class
    USER_STATE[user_id]['step'] = 'get_task_text'
    bot.send_message(user_id, f"Вы выбрали класс {school_class}. Теперь введите текст задания:")

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'get_task_text')
def process_task_text(message):
    user_id = message.chat.id
    USER_STATE[user_id]['task_text'] = message.text
    USER_STATE[user_id]['step'] = 'get_task_points'
    bot.send_message(user_id, "Введите количество баллов за выполнение этого задания:")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("correct_", "wrong_")))
def review_answer(call):
    task_id = int(call.data.split("_")[1])
    is_correct = call.data.startswith("correct_")
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Получаем информацию о задании, включая баллы
    c.execute("SELECT student_id, teacher_id, points FROM tasks WHERE id=?", (task_id,))
    student_id, teacher_id, points = c.fetchone()
    
    # Обновляем статус задания
    status = "completed_correct" if is_correct else "completed_wrong"
    c.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    
    # Если ответ верный, добавляем баллы ученику
    if is_correct:
        c.execute("UPDATE users SET points=points+? WHERE tg_id=?", (points, student_id))
    
    conn.commit()
    conn.close()
    
    # Уведомляем ученика
    result_text = "верно" if is_correct else "неверно"
    points_text = f" +{points} баллов" if is_correct else ""
    bot.send_message(student_id, f"Учитель проверил ваш ответ: {result_text}{points_text}")
    
    # Уведомляем учителя
    bot.send_message(teacher_id, f"Вы отметили ответ как {result_text}. Ученик {'получил' if is_correct else 'не получил'} {points} баллов.")

@bot.callback_query_handler(func=lambda call: call.data == "rating")
def show_rating(call):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Показываем всех пользователей, не только активных
    c.execute("SELECT first_name, last_name, school_class, points FROM users WHERE school_class IS NOT NULL ORDER BY points DESC")
    users = c.fetchall()
    conn.close()
    
    if not users:
        bot.send_message(call.message.chat.id, "Пока нет зарегистрированных пользователей.")
        return
    
    # Группируем по параллелям
    parallel_users = {}
    for first_name, last_name, school_class, points in users:
        if school_class and len(school_class) > 1:
            parallel = school_class[:-1]
            parallel_users.setdefault(parallel, [])
            parallel_users[parallel].append((first_name, last_name, school_class, points))
    
    # Формируем рейтинг
    rating_text = "🏆 Рейтинг всех пользователей:\n\n"
    for parallel, users_in_parallel in parallel_users.items():
        rating_text += f"Параллель {parallel}:\n"
        for i, (fn, ln, sc, pts) in enumerate(users_in_parallel[:10], 1):  # Топ-10 для каждой параллели
            rating_text += f"{i}. {fn} {ln} ({sc}) - {pts} баллов\n"
        rating_text += "\n"
    
    bot.send_message(call.message.chat.id, rating_text)

@bot.callback_query_handler(func=lambda call: call.data == "registration")
def start_registration(call):
    user_id = call.message.chat.id
    USER_STATE[user_id] = {'step': 1}
    bot.send_message(user_id, "Введи своё имя:")

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 1)
def process_first_name(message):
    USER_STATE[message.chat.id]['first_name'] = message.text.strip()
    USER_STATE[message.chat.id]['step'] = 2
    bot.send_message(message.chat.id, "Теперь введи свою фамилию:")

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 2)
def process_last_name(message):
    user_id = message.chat.id
    USER_STATE[user_id]['last_name'] = message.text.strip()
    first_name = USER_STATE[user_id]['first_name']
    last_name = USER_STATE[user_id]['last_name']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Проверяем, существует ли пользователь с таким tg_id
    c.execute("SELECT * FROM users WHERE tg_id=?", (user_id,))
    existing_user = c.fetchone()
    conn.close()

    if existing_user:
        # Если пользователь существует, переходим к вводу пароля
        USER_STATE[user_id]['step'] = 'login_password'
        bot.send_message(user_id, "Вы уже зарегистрированы. Введите пароль для входа:")
    else:
        # Если пользователя нет, продолжаем регистрацию
        USER_STATE[user_id]['step'] = 3
        skip_keyboard = types.InlineKeyboardMarkup()
        skip_keyboard.add(types.InlineKeyboardButton("Пропустить", callback_data="skip_username"))
        bot.send_message(user_id, "Введи свой никнейм (или нажми 'Пропустить'):", reply_markup=skip_keyboard)

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'login_password')
def process_login_password(message):
    user_id = message.chat.id
    password = message.text.strip()
    first_name = USER_STATE[user_id]['first_name']
    last_name = USER_STATE[user_id]['last_name']

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Ищем пользователя по tg_id и паролю
    c.execute("SELECT * FROM users WHERE tg_id=? AND password=?", 
             (user_id, password))
    user = c.fetchone()
    conn.close()

    if user:
        # Активируем пользователя
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET is_active=1 WHERE tg_id=?", (user_id,))
        conn.commit()
        conn.close()
        
        role = user[8]  # индекс 8 — это поле "role"
        if role == 'teacher':
            user_keyboard = types.InlineKeyboardMarkup()
            user_keyboard.add(button_link_inline, button_rating_inline, button_quest_give_inline, button_logout_inline)
            bot.send_message(user_id, f"Добро пожаловать обратно, {first_name} {last_name}!", reply_markup=user_keyboard)
            bot.send_message(user_id, "Для навигации используйте панель ниже.", reply_markup=teacher_reply_keyboard)
        else:
            user_keyboard = types.InlineKeyboardMarkup()
            user_keyboard.add(button_link_inline, button_rating_inline, button_quest_inline, button_logout_inline)
            bot.send_message(user_id, f"Добро пожаловать обратно, {first_name} {last_name}!", reply_markup=user_keyboard)
            bot.send_message(user_id, "Для навигации используй панель ниже.", reply_markup=student_reply_keyboard)
        
        # Показываем профиль
        show_profile(message)
        del USER_STATE[user_id]
    else:
        bot.send_message(user_id, "Неверный пароль. Попробуйте еще раз:")

@bot.callback_query_handler(func=lambda call: call.data == "skip_username")
def skip_username(call):
    USER_STATE[call.message.chat.id]['username'] = None
    USER_STATE[call.message.chat.id]['step'] = 4
    send_grade_selection(call.message.chat.id)

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 3)
def process_username(message):
    USER_STATE[message.chat.id]['username'] = message.text.strip()
    USER_STATE[message.chat.id]['step'] = 4
    send_grade_selection(message.chat.id)

def send_grade_selection(user_id):
    keyboard = types.InlineKeyboardMarkup()
    for grade in range(1, 12):
        keyboard.add(types.InlineKeyboardButton(str(grade), callback_data=f"grade_{grade}"))
    bot.send_message(user_id, "Выбери свой класс (номер):", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("grade_"))
def process_grade_selection(call):
    USER_STATE[call.message.chat.id]['grade'] = call.data.split("_")[1]
    send_letter_selection(call.message.chat.id)

def send_letter_selection(user_id):
    keyboard = types.InlineKeyboardMarkup()
    for letter in ["А", "Б", "В"]:
        keyboard.add(types.InlineKeyboardButton(letter, callback_data=f"class_{letter}"))
    bot.send_message(user_id, "Выбери букву класса:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("class_"))
def process_class_selection(call):
    user_id = call.message.chat.id
    letter = call.data.split("_")[1]
    school_class = f"{USER_STATE[user_id]['grade']}{letter}"
    USER_STATE[user_id]['school_class'] = school_class
    USER_STATE[user_id]['step'] = 'set_password'
    bot.send_message(user_id, "Придумай и введи пароль для входа:")

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'set_password')
def set_password(message):
    user_id = message.chat.id
    USER_STATE[user_id]['password'] = message.text.strip()
    data = USER_STATE[user_id]

    register_user(
        first_name=data['first_name'],
        last_name=data['last_name'],
        username=data.get('username'),
        school_class=data.get('school_class'),
        role='student',
        user_id=user_id,
        password=data['password']
    )
    bot.send_message(user_id, f"Регистрация завершена!\nИмя: {data['first_name']}\nФамилия: {data['last_name']}\nКласс: {data['school_class']}")
    del USER_STATE[user_id]

if __name__ == "__main__":
    print("Бот запущен.")
    create_db()
    try:
        bot.polling(non_stop=True, interval=1)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")