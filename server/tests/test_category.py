import unittest
from app import app, db
from models import Category

class CategoryTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()

        with app.app_context():
            db.create_all()
            category = Category(name="AI", description="Artificial Intelligence")
            db.session.add(category)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.drop_all()

    def test_get_categories(self):
        res = self.client.get('/api/categories')
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.get_json(), list)
        self.assertIn("name", res.get_json()[0])

if __name__ == '__main__':
    unittest.main()
