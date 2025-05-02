import unittest
from app import app, db
from models import User

class UserRouteTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

            # Create admin user
            self.admin = User(
                username="admin",
                email="admin@moringa.admin.com"
            )
            self.admin.password = "adminpass"
            db.session.add(self.admin)
            db.session.commit()

            # Login admin to get token
            res = self.client.post('/api/login', json={
                "email": "admin@moringa.admin.com",
                "password": "adminpass"
            })
            self.token = res.get_json()["access_token"]
            self.auth_header = {
                "Authorization": f"Bearer {self.token}"
            }

    def tearDown(self):
        with app.app_context():
            db.drop_all()

    def test_get_user_profile(self):
        res = self.client.get('/api/user', headers=self.auth_header)
        self.assertEqual(res.status_code, 200)
        self.assertIn("email", res.get_json())

    def test_admin_can_fetch_all_users(self):
        res = self.client.get('/api/admin/users', headers=self.auth_header)
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.get_json(), list)

if __name__ == '__main__':
    unittest.main()
