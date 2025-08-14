from django.urls import reverse
from rest_framework import status
from investors.models import SavedStartup
from investors.tests.test_setup import BaseInvestorTestCase

class SavedStartupLoggingTests(BaseInvestorTestCase):
    def setUp(self):
        super().setUp()
        # тут створюєш self.investor, self.startup та self.list_url — у тебе це вже є в базовому сетапі

    def test_create_logs(self):
        with self.assertLogs('investors.views', level='INFO') as cap:
            res = self.client.post(self.list_url, {"startup": self.startup.id, "status": "watching"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertTrue(any("SavedStartup created" in m for m in cap.output))
        # За бажанням можна перевірити й id:
        self.assertTrue(any(f"startup={self.startup.id}" in m for m in cap.output))

    def test_update_logs(self):
        obj = SavedStartup.objects.create(investor=self.investor, startup=self.startup, status="watching")
        url = reverse("saved-startup-detail", args=[obj.id])
        with self.assertLogs('investors.views', level='INFO') as cap:
            res = self.client.patch(url, {"status": "contacted"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertTrue(any("SavedStartup updated" in m for m in cap.output))
        self.assertTrue(any(f"saved={obj.id}" in m for m in cap.output))

    def test_delete_logs(self):
        obj = SavedStartup.objects.create(investor=self.investor, startup=self.startup, status="watching")
        url = reverse("saved-startup-detail", args=[obj.id])
        with self.assertLogs('investors.views', level='INFO') as cap:
            res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT, res.data)
        self.assertTrue(any("SavedStartup deleted" in m for m in cap.output))
        self.assertTrue(any(f"saved={obj.id}" in m for m in cap.output))