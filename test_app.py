import unittest
import os
from app import app, db
from models import User, Item, Claim, CampusLocation
from matching import find_potential_matches

class CampusFindTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_01_database_seeded(self):
        with app.app_context():
            user_count = User.query.count()
            item_count = Item.query.count()
            loc_count = CampusLocation.query.count()
            claim_count = Claim.query.count()
            
            self.assertGreaterEqual(user_count, 4, "Users should be seeded")
            self.assertGreaterEqual(item_count, 8, "Items should be seeded")
            self.assertGreaterEqual(loc_count, 8, "Locations should be seeded")
            self.assertGreaterEqual(claim_count, 1, "At least one claim should be seeded")
            print(f"[PASS] DB has {user_count} users, {item_count} items, {loc_count} locations, {claim_count} claims.")

    def test_02_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CampusFind', response.data)
        self.assertIn(b'Lost It on Campus', response.data)
        print("[PASS] Homepage rendered successfully.")

    def test_03_item_catalog_and_filters(self):
        response = self.client.get('/items')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Campus Lost', response.data)

        # Filter by type=lost
        res_lost = self.client.get('/items?type=lost')
        self.assertEqual(res_lost.status_code, 200)

        # Filter by category=Electronics
        res_cat = self.client.get('/items?category=Electronics')
        self.assertEqual(res_cat.status_code, 200)

        # Search query
        res_search = self.client.get('/items?q=AirPods')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b'AirPods', res_search.data)
        print("[PASS] Item catalog and filters working.")

    def test_04_item_detail_and_smart_matching(self):
        with app.app_context():
            lost_airpods = Item.query.filter(Item.title.ilike('%AirPods Pro 2%')).first()
            self.assertIsNotNone(lost_airpods)
            
            # Test detail page
            res = self.client.get(f'/items/{lost_airpods.id}')
            self.assertEqual(res.status_code, 200)
            self.assertIn(lost_airpods.title.encode(), res.data)
            
            # Test smart matching algorithm
            found_items = Item.query.filter_by(item_type='found').all()
            matches = find_potential_matches(lost_airpods, found_items, min_score=35)
            self.assertGreater(len(matches), 0, "AirPods should find a potential match")
            self.assertGreaterEqual(matches[0]['score'], 50, "Match score should be high")
            print(f"[PASS] Smart matching scored top match at {matches[0]['score']}% for {matches[0]['item'].title}")

    def test_05_auth_and_quick_login(self):
        # Quick login as student
        res = self.client.get('/quick-login/aarav', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Aarav Sharma', res.data)

        # Check my-items dashboard
        res_my = self.client.get('/my-items')
        self.assertEqual(res_my.status_code, 200)
        self.assertIn(b'My Campus Dashboard', res_my.data)

        # Quick login as admin
        res_admin = self.client.get('/quick-login/admin', follow_redirects=True)
        self.assertEqual(res_admin.status_code, 200)
        
        # Access admin dashboard
        res_dash = self.client.get('/admin/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b'Campus Custody & Repository', res_dash.data)
        print("[PASS] Authentication, quick login, and admin access working.")

    def test_06_campus_map(self):
        res = self.client.get('/campus-map')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Campus Zone & Location', res.data)
        self.assertIn(b'Central Library', res.data)
        print("[PASS] Campus Map page rendered successfully.")

    def test_07_api_search(self):
        res = self.client.get('/api/search?q=calculator')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertIsInstance(json_data, list)
        self.assertGreaterEqual(len(json_data), 1)
        self.assertIn('Calculator', json_data[0]['title'])
        print(f"[PASS] API search returned {len(json_data)} item(s) for 'calculator'")

    def test_08_claim_pass_and_qr(self):
        # Login as student Aarav who has an approved claim
        self.client.get('/quick-login/aarav')
        with app.app_context():
            claim = Claim.query.filter_by(status='approved').first()
            self.assertIsNotNone(claim)
            claim_id = claim.id
            
        res = self.client.get(f'/claims/{claim_id}/pass')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'APPROVED PASS', res.data)
        self.assertIn(b'Handover PIN', res.data)
        print("[PASS] Claim Pass with QR code generated and accessible.")

    def test_09_export_csv(self):
        self.client.get('/quick-login/admin')
        res = self.client.get('/admin/export-csv')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Title,Category,Campus Location', res.data)
        print("[PASS] Admin CSV export generated valid dataset.")

if __name__ == '__main__':
    unittest.main()
