from django.urls import reverse
from django.contrib.auth.hashers import make_password
from rest_framework import status
from investors.models import Investor, SavedStartup
from startups.models import Startup
from users.models import User, UserRole
from investors.tests.test_setup import BaseInvestorTestCase


class SavedStartupLoggingTests(BaseInvestorTestCase):
    def setUp(self):
        super().setUp()

        # інвестор під автологіненим self.user з BaseInvestorTestCase
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

        self.list_url = reverse("saved-startup-list")

    def test_create_logs(self):
        with self.assertLogs("investors.views", level="INFO") as cap:
            res = self.client.post(
                self.list_url, {"startup": self.startup.id, "status": "watching"}, format="json"
            )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        msgs = "\n".join(r.getMessage() for r in cap.records)
        self.assertTrue("SavedStartup" in msgs and ("create" in msgs or "created" in msgs))

    def test_update_logs(self):
        obj = SavedStartup.objects.create(investor=self.investor, startup=self.startup, status="watching")
        url = reverse("saved-startup-detail", args=[obj.id])
        with self.assertLogs("investors.views", level="INFO") as cap:
            res = self.client.patch(url, {"status": "contacted"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        msgs = "\n".join(r.getMessage() for r in cap.records)
        self.assertTrue("SavedStartup" in msgs and ("update" in msgs or "updated" in msgs))

    def test_delete_logs(self):
        obj = SavedStartup.objects.create(investor=self.investor, startup=self.startup, status="watching")
        url = reverse("saved-startup-detail", args=[obj.id])
        with self.assertLogs("investors.views", level="INFO") as cap:
            res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT, res.data)
        msgs = "\n".join(r.getMessage() for r in cap.records)
        self.assertTrue("SavedStartup" in msgs and ("delete" in msgs or "deleted" in msgs))