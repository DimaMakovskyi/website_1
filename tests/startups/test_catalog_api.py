# tests/startups/test_catalog_api.py
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from startups.models import Startup, Industry, Location

User = get_user_model()


class StartupCatalogAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # користувачі
        self.owner = User.objects.create_user(email="owner@example.com", password="pass")
        self.viewer = User.objects.create_user(email="viewer@example.com", password="pass")
        self.other_owner = User.objects.create_user(email="other@example.com", password="pass")

        # автентифікація переглядача (каталог доступний лише для авторизованих)
        self.client.force_authenticate(self.viewer)

        # довідники
        self.ind_fin = Industry.objects.create(name="Fintech")
        self.ind_ai = Industry.objects.create(name="AI")

        self.loc_kyiv = Location.objects.create(country="UA", city="Kyiv")
        self.loc_lviv = Location.objects.create(country="UA", city="Lviv")

        # Дані
        # публічний стартап власника — має бути видимим усім авторизованим
        self.pub = Startup.objects.create(
            user=self.owner,
            company_name="Acme",
            industry=self.ind_fin,          # якщо у тебе M2M — після save: self.pub.industries.set([self.ind_fin])
            location=self.loc_kyiv,
            website="https://ac.me",
            email="acme@example.com",
            founded_year=2024,
            team_size=10,
            funding_needed=Decimal("500000.00"),
            stage="mvp",                    # з твоїх choices: idea/mvp/launch/scale/exit
            is_public=True,
            is_verified=True,
        )

        # приватний стартап поточного користувача — теж має бути видимим (бо власний)
        self.my_private = Startup.objects.create(
            user=self.viewer,
            company_name="MyPrivate",
            industry=self.ind_ai,
            location=self.loc_lviv,
            website="https://me.example",
            email="me@example.com",
            founded_year=2024,
            team_size=3,
            funding_needed=Decimal("10000.00"),
            stage="idea",
            is_public=False,                # приватний
            is_verified=False,
        )

        # приватний стартап іншого користувача — НЕ має бути видимим
        self.other_private = Startup.objects.create(
            user=self.other_owner,
            company_name="Hidden",
            industry=self.ind_ai,
            location=self.loc_lviv,
            website="https://hidden.example",
            email="hidden@example.com",
            founded_year=2023,
            team_size=7,
            funding_needed=Decimal("20000.00"),
            stage="idea",
            is_public=False,                # приватний
            is_verified=True,
        )

        # базові URL-и через reverse (імена від DRF router)
        self.list_url = reverse("startup-list")                 # /api/v1/startups/
        self.detail_url = lambda pk: reverse("startup-detail", args=[pk])  # /api/v1/startups/{id}/

    # ---------- ПЕРМІШЕНИ ----------
    def test_list_requires_auth(self):
        client = APIClient()  # без авторизації
        resp = client.get(self.list_url)
        self.assertIn(resp.status_code, (401, 403))

    def test_detail_requires_auth(self):
        client = APIClient()  # без авторизації
        resp = client.get(self.detail_url(self.pub.id))
        self.assertIn(resp.status_code, (401, 403))

    # ---------- СПИСОК / ВИДИМІСТЬ ----------
    def test_list_includes_public_and_my_private(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, 200)
        ids = {item["id"] for item in resp.data}
        self.assertIn(self.pub.id, ids)            # публічний є
        self.assertIn(self.my_private.id, ids)     # мій приватний є
        self.assertNotIn(self.other_private.id, ids)  # чужий приватний – нема

    # ---------- ФІЛЬТРИ ----------
    def test_filter_by_industry_name(self):
        resp = self.client.get(self.list_url, {"industry": "Fintech"})
        self.assertEqual(resp.status_code, 200)
        ids = {item["id"] for item in resp.data}
        self.assertIn(self.pub.id, ids)
        self.assertNotIn(self.my_private.id, ids)  # бо my_private -> AI

    def test_filter_by_min_team_size(self):
        resp = self.client.get(self.list_url, {"min_team_size": 5})
        self.assertEqual(resp.status_code, 200)
        ids = {item["id"] for item in resp.data}
        self.assertIn(self.pub.id, ids)            # team_size=10
        # мій приватний team_size=3 -> має відфільтруватися
        self.assertNotIn(self.my_private.id, ids)

    def test_filter_by_funding_needed_lte(self):
        # ліміт 20k залишить тільки ті, де funding_needed <= 20000
        resp = self.client.get(self.list_url, {"funding_needed__lte": 20000})
        self.assertEqual(resp.status_code, 200)
        ids = {item["id"] for item in resp.data}
        self.assertIn(self.my_private.id, ids)     # 10k
        self.assertNotIn(self.pub.id, ids)         # 500k

    def test_filter_by_country_and_city(self):
        # pub -> UA, Kyiv; my_private -> UA, Lviv
        resp = self.client.get(self.list_url, {"country": "UA", "city": "Kyiv"})
        self.assertEqual(resp.status_code, 200)
        ids = {item["id"] for item in resp.data}
        self.assertIn(self.pub.id, ids)
        self.assertNotIn(self.my_private.id, ids)

    def test_filter_by_is_verified(self):
        resp = self.client.get(self.list_url, {"is_verified": True})
        self.assertEqual(resp.status_code, 200)
        ids = {item["id"] for item in resp.data}
        self.assertIn(self.pub.id, ids)            # verified=True
        self.assertNotIn(self.my_private.id, ids)  # verified=False

    # ---------- ДЕТАЛІ ----------
    def test_detail_returns_object(self):
        resp = self.client.get(self.detail_url(self.pub.id))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], self.pub.id)
        # базові поля
        self.assertEqual(resp.data["company_name"], "Acme")
        self.assertIn("industry", resp.data)
        self.assertIn("location", resp.data)

    # ---------- ПОШУК (опційно, якщо ES піднятий) ----------
    # Якщо хочеш стабільний тест без ES — можна пропустити або приймати (200 або 503)
    def test_search_endpoint_reachable(self):
        url = reverse("startups-search-list")  # /api/v1/startups/search/
        resp = self.client.get(url, {"search": "Acme"})
        self.assertIn(resp.status_code, (200, 503))
