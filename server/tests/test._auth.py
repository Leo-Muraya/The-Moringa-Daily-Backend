import unittest
from app import app, db
from models import User

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_register_success(self):
        res = self.client.post('/api/register', json={
            "username": "testuser",
            "email": "test@moringa.student.com",
            "password": "testpass"
        })
        self.assertEqual(res.status_code, 201)
        self.assertIn("username", res.get_json())

    def test_login_success(self):
        # Register
        self.client.post('/api/register', json={
            "username": "testuser",
            "email": "test@moringa.student.com",
            "password": "testpass"
        })
        # Login
        res = self.client.post('/api/login', json={
            "email": "test@moringa.student.com",
            "password": "testpass"
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("access_token", res.get_json())

if __name__ == '__main__':
    unittest.main()
