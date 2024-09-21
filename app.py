from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
import pandas as pd
from werkzeug.utils import secure_filename
import os


# Set up folder for file uploads
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(10), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    section = db.Column(db.String(2), nullable=False)
    stream  = db.Column(db.String(10), nullable=False)
    classroom = db.Column(db.String(10))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def add_column(column_name, column_type):
    with app.app_context():
        existing_columns = db.session.execute(text("PRAGMA table_info(student)")).fetchall()
        existing_column_names = {col[1] for col in existing_columns}
        if column_name not in existing_column_names:
            db.session.execute(text("ALTER TABLE student ADD COLUMN {} {}".format(column_name, column_type)))
            db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('add_student_form'))
        else:
            flash('Invalid credentials')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    candidate_id = request.form['candidate_id']
    name = request.form['name']
    section = request.form['section']
    stream = request.form['stream']
    classroom = request.form['classroom']
    
    # Dynamically add data for new columns if they exist
    student_data = {'candidate_id': candidate_id, 'name': name, 'section': section, 'stream': stream, 'classroom': classroom}

    for column in request.form:
        if column not in student_data:
            setattr(Student, column, request.form[column])

    new_student = Student(**student_data)
    db.session.add(new_student)
    db.session.commit()
    return jsonify({'message': 'Student added successfully!'})

@app.route('/add_student_form', methods=['GET'])
@login_required
def add_student_form():
    columns = db.session.execute(text("PRAGMA table_info(student)")).fetchall()
    extra_fields = [col[1] for col in columns if col[1] not in ['id', 'candidate_id', 'name', 'stream', 'section', 'classroom']]
    
    return render_template('add_student.html', extra_fields=extra_fields)

@app.route('/add_field', methods=['GET', 'POST'])
@login_required
def add_field():
    if request.method == 'POST':
        field_name = request.form['field_name']
        field_type = request.form['field_type']
        add_column(field_name, field_type)
        return redirect(url_for('add_field'))
    return render_template('add_field.html')

# @app.route('/get_student', methods=['GET'])
# def get_student_by_form():
#     student_id = request.args.get('student_id')
#     if student_id:        
#         student = Student.query.filter_by(candidate_id=student_id).first()
#         if student:
#             columns = db.session.execute(text("PRAGMA table_info(student)")).fetchall()
#             student_data = {col[1]: getattr(student, col[1], None) for col in columns[1:]}
#             return render_template('index.html', student=student_data, student_id=student_id)
#         else:
#             return render_template('index.html', message="Enter Student ID!")
#     return render_template('index.html')

@app.route('/get_student', methods=['GET'])
def get_student_by_form():
    student_id = request.args.get('student_id')
    student_name = request.args.get('student_name')

    # If searching by student ID
    if student_id:
        student = Student.query.filter_by(candidate_id=student_id).first()
        if student:
            columns = db.session.execute(text("PRAGMA table_info(student)")).fetchall()
            student_data = {col[1]: getattr(student, col[1], None) for col in columns[1:]}
            return render_template('index.html', student=student_data, student_id=student_id)
        else:
            return render_template('index.html', message="No student found with this ID.")

    # If searching by name
    elif student_name:

        students = Student.query.filter(Student.name.ilike("{}".format(student_name))).all()
        if len(students) == 1:
            # Single student found
            student = students[0]
            columns = db.session.execute(text("PRAGMA table_info(student)")).fetchall()
            student_data = {col[1]: getattr(student, col[1], None) for col in columns[1:]}
            return render_template('index.html', student=student_data)
        elif len(students) > 1:
            # Multiple students found
            return render_template('index.html', students=students)
        else:
            return render_template('index.html', message="No student found with this name.")

    return render_template('index.html')

# Route for searching student names for the autocomplete feature
@app.route('/search_names', methods=['GET'])
def search_names():
    search_term = request.args.get('name')
    if search_term:
        students = Student.query.filter(Student.name.ilike("{}%".format(search_term))).all()
        suggestions = [student.name for student in students]
        return jsonify(suggestions=suggestions)
    return jsonify(suggestions=[])



@app.route('/edit_student', methods=['GET'])
@login_required
def edit_student_form():
    student_id = request.args.get('student_id')
    if student_id:
        student = db.session.get(Student, student_id)
        if student:
            # Fetch column names and types dynamically from the table
            columns = db.session.execute(text("PRAGMA table_info(student)")).fetchall()
            student_data = {col[1]: getattr(student, col[1], '') for col in columns}
            return render_template('edit_student.html', student=student_data)
        else:
            flash("Enter Student IDS!")
            return redirect(url_for('index'))
    return redirect(url_for('edit_student'))

@app.route('/update_student', methods=['POST'])
@login_required
def update_student():
    student_id = request.form.get('student_id')
    
    if student_id:
        student = db.session.get(Student, student_id)
        if student:
            columns = db.session.execute(text("PRAGMA table_info(student)")).fetchall()
            
            for col in columns:
                column_name = col[1]
                if column_name != 'id':
                    print(column_name)
                    new_value = request.form.get(column_name, '')

                    db.session.execute(text("UPDATE student SET {} = '{}' WHERE id={}".format(column_name,new_value,student_id)))
                    db.session.commit()
            
            db.session.commit()
            flash("Student data updated successfully!")
            return redirect(url_for('get_student_by_form', student_id=student_id))
        else:
            flash("Enter Student ID!")
            return redirect(url_for('index'))
    
    return redirect(url_for('index'))

@app.route('/import_data', methods=['GET', 'POST'])
def import_data():
    if request.method == 'POST':
        # Check if file is submitted
        file = request.files.get('file')
        if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
            # Save file to upload folder
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process CSV or Excel file
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            elif filename.endswith('.xlsx'):
                df = pd.read_excel(filepath)
            print([row for index, row in df.iterrows()])
            # Process data from file and insert it into the database
            for index, row in df.iterrows():
                new_student = Student(
                    candidate_id=row['candidate_id'],
                    name=row['name'],
                    stream=row['stream'],
                    section=row.get('section', ''),
                    classroom=row.get('classroom', '')
                    # Add other fields as necessary
                )
                db.session.add(new_student)
            
            db.session.commit()
            flash('Data imported successfully!')
            return redirect(url_for('import_data'))
        
        else:
            flash('Invalid file type. Please upload a CSV or Excel file.')
            return redirect(url_for('import_data'))
    
    return render_template('index.html')

@app.route('/view_students', methods=['GET'])
def view_students():
    students = Student.query.order_by(Student.classroom).all()
    return render_template('view_students.html', students=students)

if __name__ == '__main__':
    app.run(debug=False)
