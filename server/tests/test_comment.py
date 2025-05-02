import unittest
from app import app, db
from models import User, Category, Content, ContentType

class CommentTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Create user and login
            self.user = User(username="kibe", email="kibe@moringa.student.com")
            self.user.password = "securepass"
            db.session.add(self.user)

            # Create category and content
            self.category = Category(name="Backend", description="APIs")
            db.session.add(self.category)
            db.session.commit()

            self.content = Content(
                title="Testing APIs",
                body="Unittest is cool.",
                content_type=ContentType.ARTICLE,
                author_id=self.user.id,
                category_id=self.category.id
            )
            db.session.add(self.content)
            db.session.commit()

            # Login
            res = self.client.post('/api/login', json={
                "email": "kibe@moringa.student.com",
                "password": "securepass"
            })
            self.token = res.get_json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        with app.app_context():
            db.drop_all()

    def test_add_comment(self):
        res = self.client.post('/api/comments', json={
            "content_id": self.content.id,
            "body": "Great article!"
        }, headers=self.headers)

        self.assertEqual(res.status_code, 201)
        self.assertIn("body", res.get_json())

    def test_get_comments_for_content(self):
        self.test_add_comment()
        res = self.client.get(f'/api/content/{self.content.id}/comments')
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.get_json(), list)

if __name__ == '__main__':
    unittest.main()
