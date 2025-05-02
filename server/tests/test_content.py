import unittest
from app import app, db
from models import User, Category, ContentType

class ContentRouteTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            self.user = User(username="jane", email="jane@moringa.student.com")
            self.user.password = "mypassword"
            db.session.add(self.user)

            self.category = Category(name="Dev", description="Dev content")
            db.session.add(self.category)

            db.session.commit()

            res = self.client.post('/api/login', json={
                "email": "jane@moringa.student.com",
                "password": "mypassword"
            })
            self.token = res.get_json()["access_token"]
            self.headers = {
                "Authorization": f"Bearer {self.token}"
            }

    def tearDown(self):
        with app.app_context():
            db.drop_all()

    def test_create_content(self):
        res = self.client.post('/api/content', json={
            "title": "Hello Devs",
            "body": "Welcome to development.",
            "content_type": "article",
            "category_id": self.category.id
        }, headers=self.headers)

        self.assertEqual(res.status_code, 201)
        self.assertIn("title", res.get_json())

    def test_get_all_content(self):
        self.test_create_content()
        res = self.client.get('/api/content')
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.get_json(), list)

    def test_get_content_by_id(self):
        # First create content
        content_res = self.client.post('/api/content', json={
            "title": "Intro to Flask",
            "body": "Flask is awesome!",
            "content_type": "article",
            "category_id": self.category.id
        }, headers=self.headers)
        content_id = content_res.get_json()["id"]

        # Then fetch by ID
        res = self.client.get(f'/api/content/{content_id}')
        self.assertEqual(res.status_code, 200)
        self.assertIn("title", res.get_json())

if __name__ == '__main__':
    unittest.main()
