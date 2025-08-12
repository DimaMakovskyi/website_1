from django.urls import reverse
from django.contrib.auth.hashers import make_password
from rest_framework import status

from investors.models import Investor, SavedStartup
from startups.models import Startup
from users.models import User, UserRole
from investors.tests.test_setup import BaseInvestorTestCase


class SavedStartupAPITests(BaseInvestorTestCase):
    def setUp(self):
        super().setUp()

        # 1) профіль інвестора для self.user (як у твоїх API-тестах)
        self.investor = Investor.objects.create(
            user=self.user,
            industry=self.industry,
            company_name="API Capital",
            location=self.location,
            email="api.capital@example.com",
            founded_year=2020,
            team_size=5,
            stage="mvp",
            fund_size="1000000.00",
        )

        # 2) власник стартапу + сам стартап
        role_user = UserRole.objects.get(role="user")
        self.startup_owner = User.objects.create(
            email="startup.owner@example.com",
            password=make_password("Pass123!"),
            first_name="Star",
            last_name="Tup",
            role=role_user,
        )
        self.startup = Startup.objects.create(
            user=self.startup_owner,
            industry=self.industry,
            company_name="Cool Startup",
            location=self.location,
            email="info@coolstartup.com",
            founded_year=2020,
            team_size=10,
            stage="mvp",
        )

        self.list_url = reverse("saved-startup-list")  # /api/v1/investors/saved/

    def test_create_saved_startup(self):
        payload = {"startup_id": self.startup.id, "status": "watching", "notes": "цікавий кейс"}
        res = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(SavedStartup.objects.count(), 1)
        obj = SavedStartup.objects.first()
        self.assertEqual(obj.investor, self.investor)
        self.assertEqual(obj.startup, self.startup)
        # у відповіді повертається investor_id і вкладений startup
        self.assertEqual(res.data["investor_id"], self.investor.id)
        self.assertEqual(res.data["startup"]["id"], self.startup.id)

    def test_cannot_save_duplicate(self):
        SavedStartup.objects.create(investor=self.investor, startup=self.startup, status="watching")
        res = self.client.post(self.list_url, {"startup_id": self.startup.id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Already saved", str(res.data))

    def test_list_only_current_investor(self):
        # запис іншого інвестора
        role_user = UserRole.objects.get(role="user")
        other_user = User.objects.create(
            email="investor2@example.com",
            password=make_password("Pass123!"),
            first_name="Petro",
            last_name="Second",
            role=role_user,
        )
        other_investor = Investor.objects.create(
            user=other_user,
            industry=self.industry,
            company_name="Another Capital",
            location=self.location,
            email="another.capital@example.com",
            founded_year=2021,
            team_size=3,
            stage="idea",
            fund_size="500000.00",
        )
        SavedStartup.objects.create(investor=other_investor, startup=self.startup, status="watching")

        # наш запис
        my_obj = SavedStartup.objects.create(investor=self.investor, startup=self.startup, status="watching")

        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], my_obj.id)

    def test_patch_status(self):
        obj = SavedStartup.objects.create(investor=self.investor, startup=self.startup, status="watching")
        detail_url = reverse("saved-startup-detail", args=[obj.id])  # /api/v1/investors/saved/<id>/
        res = self.client.patch(detail_url, {"status": "contacted"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        obj.refresh_from_db()
        self.assertEqual(obj.status, "contacted")

    def test_delete_saved(self):
        obj = SavedStartup.objects.create(investor=self.investor, startup=self.startup, status="watching")
        detail_url = reverse("saved-startup-detail", args=[obj.id])
        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SavedStartup.objects.filter(id=obj.id).exists())

    def test_only_investor_can_save(self):
        # автентифікуємося користувачем БЕЗ investor-профілю
        role_user = UserRole.objects.get(role="user")
        plain_user = User.objects.create(
            email="plain@example.com",
            password=make_password("Pass123!"),
            first_name="No",
            last_name="Investor",
            role=role_user,
        )
        self.client.force_authenticate(user=plain_user)

        res = self.client.post(self.list_url, {"startup_id": self.startup.id}, format="json")
        # у тебе серіалізатор піднімає ValidationError => 400
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only investors", str(res.data))