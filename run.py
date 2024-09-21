from app import db, User, app
from werkzeug.security import generate_password_hash

def create_admin_user():
    # Create an admin user if it doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password=generate_password_hash('adminpassword'))
        db.session.add(admin)
        db.session.commit()

def create_tables():
    with app.app_context():
        db.create_all()
        create_admin_user()

if __name__ == '__main__':
    create_tables()
