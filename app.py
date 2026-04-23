import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'health.db')
app.config['SECRET_KEY'] = 'mindcare2024'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    patient = db.relationship('Patient', backref='user', uselist=False)


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    emergency_contact = db.Column(db.String(100))
    doctor_notes = db.Column(db.Text)
    mental_health_score = db.Column(db.Integer)
    score_label = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─── Auth ───────────────────────────────────────────────

@app.route('/')
def index():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('index.html', users=users, username=session.get('username'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))
        new_user = User(username=username, email=email,
                        password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─── User CRUD ──────────────────────────────────────────

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('update.html', user=user)


@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/users')
def users():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('users.html', users=User.query.all())


# ─── Patient Record ─────────────────────────────────────

@app.route('/patient', methods=['GET', 'POST'])
def patient():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user_id = session['user_id']
    record = Patient.query.filter_by(user_id=user_id).first()
    if request.method == 'POST':
        if record:
            record.full_name = request.form['full_name']
            record.age = request.form['age']
            record.gender = request.form['gender']
            record.emergency_contact = request.form['emergency_contact']
            record.doctor_notes = request.form['doctor_notes']
            record.updated_at = datetime.utcnow()
        else:
            record = Patient(
                user_id=user_id,
                full_name=request.form['full_name'],
                age=request.form['age'],
                gender=request.form['gender'],
                emergency_contact=request.form['emergency_contact'],
                doctor_notes=request.form['doctor_notes']
            )
            db.session.add(record)
        db.session.commit()
        flash('Patient record saved!', 'success')
        return redirect(url_for('patient'))
    return render_template('patient.html', record=record)


# ─── Quiz ───────────────────────────────────────────────

@app.route('/quiz')
def quiz():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('quiz.html')


@app.route('/quiz/submit', methods=['POST'])
def quiz_submit():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    # Each answer: 0=Not at all, 1=Several days, 2=More than half, 3=Nearly every day
    score = 0
    for i in range(1, 6):
        val = request.form.get(f'q{i}', '0')
        score += int(val)

    if score <= 4:
        label = 'Minimal / No Depression'
        color = 'success'
    elif score <= 9:
        label = 'Mild Depression'
        color = 'warning'
    elif score <= 14:
        label = 'Moderate Depression'
        color = 'orange'
    else:
        label = 'Severe Depression'
        color = 'danger'

    # Save score to patient record
    user_id = session['user_id']
    record = Patient.query.filter_by(user_id=user_id).first()
    if record:
        record.mental_health_score = score
        record.score_label = label
        record.updated_at = datetime.utcnow()
        db.session.commit()

    return render_template('quiz_result.html', score=score, label=label, color=color,
                           has_record=record is not None)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)