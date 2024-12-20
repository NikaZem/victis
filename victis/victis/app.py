import io
from flask import send_file
from flask import Flask, render_template, redirect, url_for, request, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import matplotlib
matplotlib.use('Agg')  # Устанавливаем backend для серверного приложения
import matplotlib.pyplot as plt


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habits.db'
app.config['SQLALCHEMY_BINDS'] = {'users': 'sqlite:///users.db'}
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_days = db.Column(db.Integer, default=0)
    target_days = db.Column(db.Integer, nullable=False, default=365)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Внешний ключ
    is_deleted = db.Column(db.Boolean, default=False)

    def days_count(self):
        return (datetime.utcnow() - self.start_date).days

    def days_left(self):
        return max(0, self.target_days - self.completed_days)

    def is_goal_reached(self):
        return self.completed_days >= self.target_days



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    habits = db.relationship('Habit', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/hello/')
def hello():
    return render_template('hello.html')


@app.route('/home', methods=['GET'])
@login_required
def home():
    # Привычки текущего пользователя, которые ещё не завершены
    habits = Habit.query.filter(
        Habit.user_id == current_user.id,
        Habit.is_deleted == False,
        Habit.completed_days < Habit.target_days
    ).all()

    # Привычки текущего пользователя, которые завершены
    completed_habits = Habit.query.filter(
        Habit.user_id == current_user.id,
        Habit.is_deleted == False,
        Habit.completed_days >= Habit.target_days
    ).all()

    return render_template('home.html', habits=habits, completed_habits=completed_habits, generate_motivation=generate_motivation)



@app.route('/home/add', methods=['GET', 'POST'])
@login_required
def add_habit():
    if request.method == 'POST':
        habit_name = request.form['habit_name']
        habit_description = request.form['habit_description']
        habit_target_days = int(request.form['habit_target_days'])

        if not habit_name:
            flash('Название привычки не может быть пустым!', 'error')
        else:
            new_habit = Habit(
                name=habit_name,
                description=habit_description,
                target_days=habit_target_days,
                user_id=current_user.id  # Указываем ID текущего пользователя
            )
            db.session.add(new_habit)
            db.session.commit()
            flash('Привычка успешно добавлена!', 'success')
            return redirect(url_for('home'))

    return render_template('add_habit.html')


@app.route('/delete/<int:id>')
@login_required
def delete(id):
    habit = Habit.query.get_or_404(id)
    db.session.delete(habit)
    db.session.commit()
    flash('Привычка успешно удалена!', 'success')
    return redirect(url_for('home'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    habit = Habit.query.get_or_404(id)
    if request.method == 'POST':
        habit.name = request.form['habit_name']
        habit.description = request.form['habit_description']
        habit.target_days = int(request.form['habit_target_days'])
        db.session.commit()
        flash('Привычка успешно обновлена!', 'success')
        return redirect(url_for('home'))

    return render_template('edit.html', habit=habit)



@app.route('/complete/<int:id>', methods=['POST'])
@login_required
def complete(id):
    habit = Habit.query.get_or_404(id)

    # Увеличиваем выполненные дни
    habit.completed_days += 1
    db.session.commit()

    # Формируем ответ с обновлёнными данными
    response = {
        "habit_id": habit.id,
        "completed_days": habit.completed_days,
        "days_left": habit.days_left(),
        "is_goal_reached": habit.is_goal_reached(),
        "motivation": generate_motivation((habit.completed_days / habit.target_days) * 100)
    }
    return response


@app.route('/delete_chart/<int:id>', methods=['POST'])
@login_required
def delete_chart(id):
    completed_habits = session.get('completed_habits', [])
    if id in completed_habits:
        completed_habits.remove(id)
        session['completed_habits'] = completed_habits
        session.modified = True
    return {"success": True}



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('hello'))
        else:
            flash('Неверное имя пользователя или пароль.', 'error')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует.', 'error')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация выполнена успешно!', 'success')
            return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'success')
    return redirect(url_for('index'))


def generate_motivation(completed_percentage):
    if completed_percentage < 50:
        return "Надо поднажать!"
    elif 50 <= completed_percentage < 70:
        return "Так держать!"
    elif 70 <= completed_percentage < 100:
        return "Совсем чуть-чуть!"
    else:
        return "Поздравляем с достижением цели!"


def create_progress_chart(habit):
    fig, ax = plt.subplots()
    completed = habit.completed_days
    remaining = max(0, habit.target_days - completed)

    ax.pie([completed, remaining], labels=["Выполнено", "Осталось"], autopct="%1.1f%%", colors=['#4CAF50', '#FFC107'])
    ax.set_title(f'Прогресс по привычке: {habit.name}')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return buf


@app.route('/progress_chart/<int:habit_id>')
@login_required
def progress_chart(habit_id):
    habit = Habit.query.get_or_404(habit_id)

    # Данные для графика
    labels = ['Выполнено', 'Осталось']
    values = [habit.completed_days, habit.days_left()]
    colors = ['#4CAF50', '#FF5252']

    # Построение графика
    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
    ax.axis('equal')  # Сделать график круглым
    ax.set_title(f'Прогресс: {habit.name}')

    # Сохранение графика в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)

    return send_file(buf, mimetype='image/png')


if __name__ == '__main__':
    app.run(debug=True)
