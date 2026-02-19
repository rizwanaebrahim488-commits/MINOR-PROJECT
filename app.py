"""
COMPLETE STUDENT ATTENDANCE & PROGRESS TRACKER
- Login for Student, Teacher, Parent
- Mark Attendance
- Update Progress
- View Reports
- SMS Notifications (optional)
"""
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os

# Load config
from config import DevelopmentConfig

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# Database
db = SQLAlchemy(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==================== DATABASE MODELS ====================

class User(UserMixin, db.Model):
    """Base User Model"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'teacher', 'parent'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='user', uselist=False)
    teacher = db.relationship('Teacher', backref='user', uselist=False)
    parent = db.relationship('Parent', backref='user', uselist=False)
    
    def set_password(self, password):
        """Hash password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    """Student Details"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')
    progress_records = db.relationship('Progress', backref='student', lazy=True, cascade='all, delete-orphan')
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'))

class Teacher(db.Model):
    """Teacher Details"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='teacher', lazy=True, cascade='all, delete-orphan')
    progress_records = db.relationship('Progress', backref='teacher', lazy=True, cascade='all, delete-orphan')

class Parent(db.Model):
    """Parent Details"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    
    # Relationships
    students = db.relationship('Student', backref='parent_user', lazy=True)

class Attendance(db.Model):
    """Attendance Records"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    present = db.Column(db.Boolean, default=False)
    remarks = db.Column(db.String(500))
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)

class Progress(db.Model):
    """Student Progress/Marks"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    assignment_name = db.Column(db.String(200), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    total_marks = db.Column(db.Float, default=100.0)
    percentage = db.Column(db.Float)
    date = db.Column(db.Date, nullable=False)
    comments = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_percentage(self):
        """Calculate percentage"""
        if self.total_marks > 0:
            self.percentage = (self.marks_obtained / self.total_marks) * 100

# ==================== LOGIN FUNCTIONS ====================

@login_manager.user_loader
def load_user(user_id):
    """Load user from database"""
    return User.query.get(int(user_id))

# ==================== HELPER FUNCTIONS ====================

def get_attendance_percentage(student_id, days=30):
    """Get attendance percentage"""
    from_date = datetime.now().date() - timedelta(days=days)
    
    total = Attendance.query.filter(
        Attendance.student_id == student_id,
        Attendance.date >= from_date
    ).count()
    
    if total == 0:
        return 0
    
    present = Attendance.query.filter(
        Attendance.student_id == student_id,
        Attendance.date >= from_date,
        Attendance.present == True
    ).count()
    
    return (present / total) * 100

def get_average_marks(student_id, subject=None):
    """Get average marks"""
    query = Progress.query.filter(Progress.student_id == student_id)
    
    if subject:
        query = query.filter(Progress.subject == subject)
    
    records = query.all()
    
    if not records:
        return 0
    
    total = sum(record.percentage for record in records)
    return total / len(records)

# ==================== ROUTES ====================

# --------- LOGIN & REGISTER ---------

@app.route('/', methods=['GET', 'POST'])
def login():
    """Login Page"""
    if current_user.is_authenticated:
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        elif current_user.role == 'parent':
            return redirect(url_for('parent_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif user.role == 'parent':
                return redirect(url_for('parent_dashboard'))
        else:
            flash('❌ Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register New User"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if User.query.filter_by(username=username).first():
            flash('❌ Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('❌ Email already registered', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('✅ Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """Logout User"""
    logout_user()
    flash('✅ You have been logged out', 'info')
    return redirect(url_for('login'))

# --------- STUDENT ROUTES ---------

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    """Student Dashboard"""
    if current_user.role != 'student':
        flash('❌ Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if not student:
        flash('❌ Student profile not found', 'error')
        return redirect(url_for('logout'))
    
    attendance_30 = get_attendance_percentage(student.id, days=30)
    attendance_60 = get_attendance_percentage(student.id, days=60)
    
    recent_attendance = Attendance.query.filter_by(student_id=student.id).order_by(
        Attendance.date.desc()
    ).limit(10).all()
    
    recent_progress = Progress.query.filter_by(student_id=student.id).order_by(
        Progress.date.desc()
    ).limit(5).all()
    
    return render_template('student_dashboard.html',
                         student=student,
                         attendance_30=attendance_30,
                         attendance_60=attendance_60,
                         recent_attendance=recent_attendance,
                         recent_progress=recent_progress)

# --------- PARENT ROUTES ---------

@app.route('/parent/dashboard')
@login_required
def parent_dashboard():
    """Parent Dashboard"""
    if current_user.role != 'parent':
        flash('❌ Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    parent = Parent.query.filter_by(user_id=current_user.id).first()
    
    if not parent:
        flash('❌ Parent profile not found', 'error')
        return redirect(url_for('logout'))
    
    students = parent.students
    
    student_data = []
    for student in students:
        attendance = get_attendance_percentage(student.id)
        avg_marks = get_average_marks(student.id)
        
        student_data.append({
            'student': student,
            'attendance': attendance,
            'avg_marks': avg_marks
        })
    
    return render_template('parent_dashboard.html', student_data=student_data)

@app.route('/parent/view-student/<int:student_id>')
@login_required
def parent_view_student(student_id):
    """Parent View Student Details"""
    if current_user.role != 'parent':
        flash('❌ Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.get(student_id)
    
    if not student:
        flash('❌ Student not found', 'error')
        return redirect(url_for('parent_dashboard'))
    
    parent = Parent.query.filter_by(user_id=current_user.id).first()
    
    if student.parent_id != parent.id:
        flash('❌ You cannot view this student', 'error')
        return redirect(url_for('parent_dashboard'))
    
    attendance_records = Attendance.query.filter_by(student_id=student_id).order_by(
        Attendance.date.desc()
    ).limit(30).all()
    
    progress_records = Progress.query.filter_by(student_id=student_id).order_by(
        Progress.date.desc()
    ).all()
    
    attendance_percentage = get_attendance_percentage(student_id)
    average_marks = get_average_marks(student_id)
    
    return render_template('parent_view_student.html',
                         student=student,
                         attendance_records=attendance_records,
                         progress_records=progress_records,
                         attendance_percentage=attendance_percentage,
                         average_marks=average_marks)

# --------- TEACHER ROUTES ---------

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    """Teacher Dashboard"""
    if current_user.role != 'teacher':
        flash('❌ Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    
    if not teacher:
        flash('❌ Teacher profile not found', 'error')
        return redirect(url_for('logout'))
    
    students = Student.query.filter_by(class_name=teacher.department).all()
    
    return render_template('teacher_dashboard.html',
                         teacher=teacher,
                         total_students=len(students))

@app.route('/teacher/mark-attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    """Mark Attendance"""
    if current_user.role != 'teacher':
        flash('❌ Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    students = Student.query.filter_by(class_name=teacher.department).all()
    
    if request.method == 'POST':
        date_str = request.form.get('date')
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        for student in students:
            present = request.form.get(f'attendance_{student.id}') == 'on'
            remarks = request.form.get(f'remarks_{student.id}', '')
            
            existing = Attendance.query.filter_by(
                student_id=student.id,
                teacher_id=teacher.id,
                date=attendance_date
            ).first()
            
            if existing:
                existing.present = present
                existing.remarks = remarks
            else:
                attendance = Attendance(
                    student_id=student.id,
                    teacher_id=teacher.id,
                    date=attendance_date,
                    present=present,
                    remarks=remarks
                )
                db.session.add(attendance)
        
        db.session.commit()
        flash('✅ Attendance marked successfully!', 'success')
        return redirect(url_for('mark_attendance'))
    
    return render_template('attendance.html', students=students)

@app.route('/teacher/update-progress', methods=['GET', 'POST'])
@login_required
def update_progress():
    """Update Student Progress"""
    if current_user.role != 'teacher':
        flash('❌ Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    students = Student.query.filter_by(class_name=teacher.department).all()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        assignment_name = request.form.get('assignment_name')
        marks = float(request.form.get('marks_obtained', 0))
        total = float(request.form.get('total_marks', 100))
        comments = request.form.get('comments', '')
        date_str = request.form.get('date')
        progress_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        progress = Progress(
            student_id=student_id,
            teacher_id=teacher.id,
            subject=teacher.subject,
            assignment_name=assignment_name,
            marks_obtained=marks,
            total_marks=total,
            date=progress_date,
            comments=comments
        )
        progress.calculate_percentage()
        
        db.session.add(progress)
        db.session.commit()
        
        flash('✅ Progress updated successfully!', 'success')
        return redirect(url_for('update_progress'))
    
    return render_template('progress.html', students=students)

@app.route('/teacher/reports')
@login_required
def reports():
    """Teacher Reports"""
    if current_user.role != 'teacher':
        flash('❌ Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    students = Student.query.filter_by(class_name=teacher.department).all()
    
    report_data = []
    for student in students:
        attendance = get_attendance_percentage(student.id)
        avg_marks = get_average_marks(student.id)
        
        report_data.append({
            'student': student,
            'attendance': round(attendance, 2),
            'avg_marks': round(avg_marks, 2)
        })
    
    return render_template('reports.html', report_data=report_data)

# --------- API ROUTES (FOR CHARTS) ---------

@app.route('/api/student-attendance-chart')
@login_required
def attendance_chart_data():
    """Attendance Chart Data"""
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 401
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    from_date = datetime.now().date() - timedelta(days=30)
    records = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.date >= from_date
    ).order_by(Attendance.date).all()
    
    labels = [r.date.strftime('%Y-%m-%d') for r in records]
    data = [1 if r.present else 0 for r in records]
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@app.route('/api/progress-marks-chart')
@login_required
def progress_chart_data():
    """Progress Chart Data"""
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 401
    
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    records = Progress.query.filter_by(student_id=student.id).order_by(
        Progress.date
    ).limit(10).all()
    
    labels = [r.assignment_name for r in records]
    data = [r.percentage for r in records]
    
    return jsonify({
        'labels': labels,
        'data': data
    })

# --------- ERROR HANDLERS ---------

@app.errorhandler(404)
def not_found(error):
    """404 Error"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    """500 Error"""
    db.session.rollback()
    return render_template('500.html'), 500

# --------- INITIALIZE DATABASE ---------

@app.before_request
def create_tables():
    """Create database tables"""
    db.create_all()

# --------- ADMIN SETUP ROUTE ---------

@app.route('/admin/setup', methods=['GET', 'POST'])
def admin_setup():
    """First-time admin setup"""
    if User.query.first() is not None:
        flash('❌ Setup already completed', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create_admin':
            admin = User(
                username='admin',
                email='admin@college.com',
                role='teacher'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            
            teacher = Teacher(
                user_id=admin.id,
                full_name='Admin Teacher',
                department='CSE-A',
                subject='Computer Science',
                phone='9999999999'
            )
            db.session.add(teacher)
            db.session.commit()
            
            flash('✅ Admin created! Username: admin, Password: admin123', 'success')
        
        elif action == 'create_student':
            roll = request.form.get('roll_number')
            name = request.form.get('full_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            class_name = request.form.get('class_name')
            
            user = User(
                username=roll,
                email=email,
                role='student'
            )
            user.set_password('student123')
            db.session.add(user)
            db.session.commit()
            
            student = Student(
                user_id=user.id,
                roll_number=roll,
                full_name=name,
                class_name=class_name,
                phone=phone
            )
            db.session.add(student)
            db.session.commit()
            
            flash(f'✅ Student {name} created!', 'success')
        
        elif action == 'create_parent':
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            
            user = User(
                username=email.split('@')[0],
                email=email,
                role='parent'
            )
            user.set_password('parent123')
            db.session.add(user)
            db.session.commit()
            
            parent = Parent(
                user_id=user.id,
                full_name=full_name,
                phone_number=phone,
                email=email
            )
            db.session.add(parent)
            db.session.commit()
            
            flash(f'✅ Parent {full_name} created!', 'success')
        
        return redirect(url_for('admin_setup'))
    
    return render_template('admin_setup.html')

# ==================== RUN APP ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Database initialized!")
    
    # For Render, it will use PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
