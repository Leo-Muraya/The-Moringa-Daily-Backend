import unittest
from app import app, db
from models import User, Category, Content, ContentType, UserRole

class AdminRouteTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Admin
            self.admin = User(username="admin", email="admin@moringa.admin.com", role=UserRole.ADMIN)
            self.admin.password = "adminpass"
            db.session.add(self.admin)

            # Regular user
            self.user = User(username="user", email="user@moringa.student.com")
            self.user.password = "userpass"
            db.session.add(self.user)

            # Category and Content
            category = Category(name="Tech", description="All tech content")
            db.session.add(category)
            db.session.commit()

            self.content = Content(
                title="Needs Approval",
                body="Pending review",
                content_type=ContentType.ARTICLE,
                author_id=self.user.id,
                category_id=category.id
            )
            db.session.add(self.content)
            db.session.commit()

            login = self.client.post('/api/login', json={
                "email": "admin@moringa.admin.com",
                "password": "adminpass"
            })
            self.token = login.get_json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        with app.app_context():
            db.drop_all()

    def test_approve_content(self):
        res = self.client.post(f'/api/admin/content/{self.content.id}/approve', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["approval_status"], "APPROVED")

    def test_deactivate_user(self):
        res = self.client.post(f'/api/admin/users/{self.user.id}/deactivate', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("deactivated", res.get_json()["message"].lower())

if __name__ == '__main__':
    unittest.main()
