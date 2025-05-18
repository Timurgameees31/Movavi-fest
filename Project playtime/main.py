import telebot
from telebot import types
import time
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import SQLAlchemyError
import sqlite3

Base = declarative_base()

# Модели данных
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    username = Column(String(100))
    password = Column(String(100), nullable=False)
    school_class = Column(String(10))
    points = Column(Integer, default=0)
    role = Column(String(20), default='student')
    is_active = Column(Boolean, default=True)
    
    tasks_student = relationship("Task", foreign_keys="Task.student_id", back_populates="student")
    tasks_teacher = relationship("Task", foreign_keys="Task.teacher_id", back_populates="teacher")

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'))
    teacher_id = Column(Integer, ForeignKey('users.id'))
    task_text = Column(Text)
    answer_text = Column(Text)
    points = Column(Integer, default=10)
    status = Column(String(20), default='pending')
    timestamp = Column(DateTime, default=func.now())
    
    student = relationship("User", foreign_keys=[student_id], back_populates="tasks_student")
    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="tasks_teacher")

# Настройка подключения к БД
engine = create_engine('sqlite:///users.db', connect_args={'check_same_thread': False})
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# Остальной код (токен бота и т.д.)
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

@bot.message_handler(func=lambda message: message.text == "FAQ")
def faq_handler(message):
    bot.send_message(message.chat.id, "Часто задаваемые вопросы доступны по ссылке:", reply_markup=types.InlineKeyboardMarkup().add(button_link_inline))

@bot.message_handler(func=lambda message: message.text == "Рейтинг пользователей")
def rating_handler(message):
    show_rating(message)

@bot.message_handler(func=lambda message: message.text == "Получить задание")
def get_task_handler(message):
    send_task(message)

@bot.message_handler(func=lambda message: message.text == "Выдать задание")
def give_task_handler(message):
    give_task(message)

@bot.message_handler(func=lambda message: message.text == "Профиль")
def profile_handler(message):
    show_profile(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "rating")
def rating_callback(call):
    show_rating(call)

@bot.message_handler(func=lambda message: message.text == "Проверить задания")
def check_tasks_handler(message):
    # Здесь нужно добавить логику для проверки заданий
    session = Session()
    try:
        teacher = session.query(User).filter_by(tg_id=message.chat.id, is_active=True).first()
        if not teacher or teacher.role != 'teacher':
            bot.send_message(message.chat.id, "Эта функция доступна только учителям.")
            return
            
        tasks = session.query(Task).filter_by(teacher_id=teacher.id, status='waiting_review').all()
        if not tasks:
            bot.send_message(message.chat.id, "Нет заданий для проверки.")
            return
            
        for task in tasks:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("Верно", callback_data=f"correct_{task.id}"),
                types.InlineKeyboardButton("Неверно", callback_data=f"wrong_{task.id}")
            )
            bot.send_message(message.chat.id, 
                           f"Задание ID {task.id} от ученика {task.student.first_name} {task.student.last_name}:\n\n{task.task_text}\n\nОтвет:\n{task.answer_text}", 
                           reply_markup=keyboard)
    except Exception as e:
        print(f"Ошибка при проверке заданий: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при загрузке заданий.")
    finally:
        session.close()

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

def calculate_level(points):
    level = 0
    required = 10  # Первый уровень - 10 очков
    while points >= required:
        level += 1
        points -= required
        required *= 2  # Каждый следующий уровень требует в 2 раза больше очков
    return level, required - points  # Возвращаем уровень и оставшиеся очки до следующего уровня

def register_user(first_name, last_name, username=None, school_class=None, role='student', user_id=None, password=None):
    session = Session()
    try:
        # Ищем существующего пользователя
        existing_user = session.query(User).filter_by(
            first_name=first_name, 
            last_name=last_name,
            password=password
        ).first()

        if existing_user:
            # Обновляем существующего пользователя
            existing_user.tg_id = user_id
            existing_user.username = username
            existing_user.school_class = school_class
            existing_user.role = role
            existing_user.is_active = True
        else:
            # Создаем нового пользователя
            new_user = User(
                tg_id=user_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                password=password,
                school_class=school_class,
                role=role,
                is_active=True
            )
            session.add(new_user)
        
        session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Ошибка регистрации: {e}")
        return False
    finally:
        session.close()
    
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
    # Деактивируем текущего пользователя
    c.execute("UPDATE users SET is_active=0 WHERE tg_id=? AND is_active=1", (user_id,))
    conn.commit()
    conn.close()

    if user_id in USER_STATE:
        del USER_STATE[user_id]
        
    bot.send_message(user_id, "Вы вышли из аккаунта. Для входа или регистрации нового аккаунта используйте кнопки ниже.", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "logout")
def logout_user_callback(call):
    user_id = call.message.chat.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Деактивация пользователя (не удаление)
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
    user_keyboard.add(button_link_inline, button_rating_inline, button_quest_give_inline, button_profile_inline, button_logout_inline)
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
    session = Session()
    try:
        # Находим пользователя по Telegram ID
        user = session.query(User).filter_by(tg_id=chat_id, is_active=True).first()
        if not user:
            bot.send_message(chat_id, "Пользователь не найден")
            return

        # Ищем задание для этого пользователя
        task = session.query(Task).filter_by(student_id=user.id, status='pending').first()
        if task:
            bot.send_message(chat_id, f"Ваше задание:\n{task.task_text}\n\nОтправьте ответ на это сообщение.")
            USER_STATE[chat_id] = {'step': 'send_answer', 'task_id': task.id}
        else:
            bot.send_message(chat_id, "У вас нет новых заданий.")
    except SQLAlchemyError as e:
        print(f"Ошибка получения задания: {e}")
        bot.send_message(chat_id, "Произошла ошибка при получении задания")
    finally:
        session.close()

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

def show_profile(user_id):
    session = Session()
    try:
        user = session.query(User).filter_by(tg_id=user_id, is_active=True).first()
        if not user:
            bot.send_message(user_id, "Профиль не найден")
            return

        if user.role == 'student':
            # Рассчитываем уровень и оставшиеся очки до следующего уровня
            level, points_to_next = calculate_level(user.points)
            
            profile_text = f"""
📌 *Профиль ученика*:
👤 *Имя:* {user.first_name} {user.last_name}
🔖 *Никнейм:* @{user.username if user.username else 'не указан'}
🏫 *Класс:* {user.school_class if user.school_class else 'не указан'}
🆔 *Telegram ID:* `{user_id}`
🏆 *Баллы:* {user.points}
📊 *Уровень:* {level}
🎯 *До следующего уровня:* {points_to_next} баллов
"""
            if user.school_class and len(user.school_class) > 1:
                parallel = user.school_class[:-1]
                # Расчет места в параллели
                count = session.query(func.count(User.id)).filter(
                    User.school_class.like(f"{parallel}%"),
                    User.points > user.points,
                    User.role == 'student',
                    User.is_active == True
                ).scalar() + 1
                
                total = session.query(func.count(User.id)).filter(
                    User.school_class.like(f"{parallel}%"),
                    User.role == 'student',
                    User.is_active == True
                ).scalar()
                
                profile_text += f"🏅 *Место в параллели:* {count} из {total}\n"
        else:
            # Логика для учителя (остается без изменений)
            tasks_given = session.query(Task).filter_by(teacher_id=user.id).count()
            tasks_checked = session.query(Task).filter(
                Task.teacher_id == user.id,
                Task.status.in_(['completed_correct', 'completed_wrong'])
            ).count()

            profile_text = f"""
📌 *Профиль учителя*:
👤 *Имя:* {user.first_name} {user.last_name}
🔖 *Никнейм:* @{user.username if user.username else 'не указан'}
🆔 *Telegram ID:* `{user_id}`
📝 *Заданий выдано:* {tasks_given}
✅ *Заданий проверено:* {tasks_checked}
"""

        bot.send_message(user_id, profile_text, parse_mode='Markdown')
    except SQLAlchemyError as e:
        print(f"Ошибка профиля: {e}")
        bot.send_message(user_id, "Ошибка загрузки профиля")
    finally:
        session.close()

@bot.callback_query_handler(func=lambda call: call.data == "profile")
def profile_callback(call):
    show_profile(call.message.chat.id
)

# При успешном входе любого пользователя
def successful_login(user_id, role):
    try:
        if user_id in USER_STATE:
            del USER_STATE[user_id]
        
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
        
        # Создаем сообщение для показа профиля
        
        show_profile(user_id)
    except Exception as e:
        print(f"Ошибка в successful_login: {e}")
        bot.send_message(user_id, "Произошла ошибка при входе. Пожалуйста, попробуйте снова.")

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'set_password')
def set_password(message):
    user_id = message.chat.id
    try:
        USER_STATE[user_id]['password'] = message.text.strip()
        data = USER_STATE[user_id]

        if register_user(
            first_name=data['first_name'],
            last_name=data['last_name'],
            username=data.get('username'),
            school_class=data.get('school_class'),
            role='student',
            user_id=user_id,
            password=data['password']
        ):
            bot.send_message(user_id, f"Регистрация завершена!\nИмя: {data['first_name']}\nФамилия: {data['last_name']}\nКласс: {data['school_class']}")
            successful_login(user_id, 'student')
        else:
            bot.send_message(user_id, "Произошла ошибка при регистрации. Пожалуйста, попробуйте снова.")
    except Exception as e:
        print(f"Ошибка в set_password: {e}")
        bot.send_message(user_id, "Произошла внутренняя ошибка. Пожалуйста, попробуйте позже.")
    finally:
        if user_id in USER_STATE:
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
    
    session = Session()
    try:
        task = session.query(Task).get(task_id)
        if not task:
            bot.send_message(user_id, "Ошибка: задание не найдено")
            return

        task.answer_text = answer
        task.status = 'waiting_review'
        session.commit()
        
        # Уведомляем учителя
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Верно", callback_data=f"correct_{task_id}"),
            types.InlineKeyboardButton("Неверно", callback_data=f"wrong_{task_id}")
        )
        bot.send_message(task.teacher.tg_id, 
                        f"Ученик отправил ответ на задание ID {task_id}:\n\n{answer}", 
                        reply_markup=keyboard)
        
        bot.send_message(user_id, "Ваш ответ отправлен учителю на проверку.")
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Ошибка отправки ответа: {e}")
        bot.send_message(user_id, "Ошибка отправки ответа")
    finally:
        session.close()
        if user_id in USER_STATE:
            del USER_STATE[user_id]

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
        
        session = Session()
        teacher = session.query(User).filter_by(tg_id=user_id, is_active=True).first()
        if not teacher:
            bot.send_message(user_id, "Ошибка: учитель не найден")
            return

        if USER_STATE[user_id]['target'] == 'student':
            # Получаем объект ученика по Telegram ID
            student_tg_id = USER_STATE[user_id]['student_id']
            student = session.query(User).filter_by(tg_id=student_tg_id, is_active=True).first()
            
            if not student:
                bot.send_message(user_id, "Ошибка: ученик не найден")
                return

            # Создаем задание с ID ученика из таблицы users
            new_task = Task(
                student_id=student.id,
                teacher_id=teacher.id,
                task_text=task_text,
                points=points,
                status='pending'
            )
            session.add(new_task)
            session.commit()
            
            bot.send_message(user_id, f"Задание успешно отправлено ученику {student.first_name} {student.last_name}.")
            try:
                bot.send_message(student_tg_id, "У вас новое задание от учителя! Нажмите кнопку 'Получить задание' для просмотра.")
            except Exception as e:
                bot.send_message(user_id, f"Задание сохранено, но не удалось уведомить ученика: {e}")
                
        else:
            # Отправка всему классу (аналогичные исправления)
            school_class = USER_STATE[user_id]['school_class']
            students = session.query(User).filter_by(school_class=school_class, role='student').all()
            
            if not students:
                bot.send_message(user_id, f"В классе {school_class} нет активных учеников.")
                return
            
            count = 0
            failed_notifications = 0
            for student in students:
                try:
                    new_task = Task(
                        student_id=student.id,
                        teacher_id=teacher.id,
                        task_text=task_text,
                        points=points,
                        status='pending'
                    )
                    session.add(new_task)
                    count += 1
                    
                    try:
                        bot.send_message(student.tg_id, "У вас новое задание от учителя! Нажмите кнопку 'Получить задание' для просмотра.")
                    except:
                        failed_notifications += 1
                        
                except Exception as e:
                    print(f"Ошибка при отправке задания ученику {student.tg_id}: {e}")
                    continue
            
            session.commit()
            
            if failed_notifications > 0:
                bot.send_message(user_id, f"Задание отправлено {count} ученикам класса {school_class}. Не удалось уведомить {failed_notifications} учеников.")
            else:
                bot.send_message(user_id, f"Задание успешно отправлено всем {count} ученикам класса {school_class}.")
        
        del USER_STATE[user_id]
        
    except ValueError:
        bot.send_message(user_id, "Количество баллов должно быть положительным числом. Попробуйте еще раз:")
    except Exception as e:
        bot.send_message(user_id, f"Произошла ошибка: {str(e)}")
        print(f"Ошибка при обработке задания: {e}")
        if 'session' in locals():
            session.rollback()
        del USER_STATE[user_id]
    finally:
        if 'session' in locals():
            session.close()

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
    
    session = Session()
    try:
        task = session.query(Task).get(task_id)
        if not task:
            return

        task.status = "completed_correct" if is_correct else "completed_wrong"
        
        if is_correct:
            task.student.points += task.points
        
        session.commit()
        
        # Уведомляем ученика
        result_text = "верно" if is_correct else "неверно"
        points_text = f" +{task.points} баллов" if is_correct else ""
        bot.send_message(task.student.tg_id, f"Учитель проверил ваш ответ: {result_text}{points_text}")
        
        # Уведомляем учителя
        bot.send_message(call.message.chat.id, 
                       f"Вы отметили ответ как {result_text}. Ученик {'получил' if is_correct else 'не получил'} {task.points} баллов.")
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Ошибка проверки задания: {e}")
    finally:
        session.close()

def show_rating(message_or_call):
    if hasattr(message_or_call, 'message'):
        chat_id = message_or_call.message.chat.id
    else:
        chat_id = message_or_call.chat.id
        
    session = Session()
    try:
        users = session.query(User).filter(
            User.school_class.isnot(None),
            User.role == 'student'
        ).order_by(User.points.desc()).all()

        if not users:
            bot.send_message(chat_id, "Нет данных для рейтинга")
            return

        rating_text = "🏆 Рейтинг пользователей:\n\n"
        parallels = {}
        
        for user in users:
            if user.school_class and len(user.school_class) > 1:
                parallel = user.school_class[:-1]
                parallels.setdefault(parallel, [])
                parallels[parallel].append(user)

        for parallel, users_in_parallel in parallels.items():
            rating_text += f"Параллель {parallel}:\n"
            for i, user in enumerate(users_in_parallel[:10], 1):
                level, _ = calculate_level(user.points)
                rating_text += f"{i}. {user.first_name} {user.last_name} ({user.school_class}) - {user.points} баллов (Ур. {level})\n"
            rating_text += "\n"

        bot.send_message(chat_id, rating_text)
    except SQLAlchemyError as e:
        print(f"Ошибка рейтинга: {e}")
        bot.send_message(chat_id, "Произошла ошибка при загрузке рейтинга")
    finally:
        session.close()
        
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

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 'login_password')
def process_login_password(message):
    user_id = message.chat.id
    password = message.text.strip()
    first_name = USER_STATE[user_id]['first_name']
    last_name = USER_STATE[user_id]['last_name']

    session = Session()
    try:
        user = session.query(User).filter_by(
            first_name=first_name,
            last_name=last_name,
            password=password
        ).first()

        if user:
            # Просто обновляем данные для входа
            user.tg_id = user_id
            user.is_active = True
            session.commit()
            
            successful_login(user_id, user.role)
        else:
            bot.send_message(user_id, "Неверный пароль. Попробуйте еще раз:")
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Ошибка входа: {e}")
    finally:
        session.close()
        if user and user.tg_id == user_id:
            del USER_STATE[user_id]

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

@bot.message_handler(func=lambda message: message.chat.id in USER_STATE and USER_STATE[message.chat.id]['step'] == 2)
def process_last_name(message):
    user_id = message.chat.id
    first_name = USER_STATE[user_id]['first_name']
    last_name = message.text.strip()
    USER_STATE[user_id]['last_name'] = last_name

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE first_name=? AND last_name=?", (first_name, last_name))
    user_exists = c.fetchone()
    conn.close()

    if user_exists:
        USER_STATE[user_id]['step'] = 'login_password'
        bot.send_message(user_id, "Введите пароль для входа:")
    else:
        USER_STATE[user_id]['step'] = 3
        skip_keyboard = types.InlineKeyboardMarkup()
        skip_keyboard.add(types.InlineKeyboardButton("Пропустить", callback_data="skip_username"))
        bot.send_message(user_id, "Введи свой никнейм (или нажми 'Пропустить'):", reply_markup=skip_keyboard)

if __name__ == "__main__":
    print("Бот запущен.")
    create_db()
    while True:
        try:
            bot.polling(non_stop=True, interval=1)
        except Exception as e:
            print(f"Ошибка в работе бота: {e}")
            print("Перезапуск через 5 секунд...")
            time.sleep(5)
