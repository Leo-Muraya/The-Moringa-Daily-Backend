import unittest
from app import app, db
from models import User, Profile

class ProfileRouteTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

            self.user = User(
                username="joan",
                email="joan@moringa.student.com"
            )
            self.user.password = "12345678"
            db.session.add(self.user)
            db.session.commit()

            login = self.client.post('/api/login', json={
                "email": "joan@moringa.student.com",
                "password": "12345678"
            })
            self.token = login.get_json()["access_token"]
            self.headers = {
                "Authorization": f"Bearer {self.token}"
            }

    def tearDown(self):
        with app.app_context():
            db.drop_all()

    def test_create_profile(self):
        res = self.client.post('/api/profile', json={
            "bio": "Software Developer",
            "profile_picture": "https://example.com/pic.jpg",
            "website": "https://joan.dev"
        }, headers=self.headers)

        self.assertEqual(res.status_code, 201)
        self.assertIn("bio", res.get_json())

    def test_get_profile(self):
        # First create profile
        self.client.post('/api/profile', json={
            "bio": "Hello world!"
        }, headers=self.headers)

        res = self.client.get('/api/profile', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("bio", res.get_json())

    def test_update_profile(self):
        # Create profile
        self.client.post('/api/profile', json={"bio": "A"}, headers=self.headers)
        # Update
        res = self.client.put('/api/profile', json={"bio": "Updated"}, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["bio"], "Updated")

if __name__ == '__main__':
    unittest.main()
