from django.urls import path
from rest_framework.routers import DefaultRouter
from investors.views import InvestorViewSet, SavedStartupViewSet, SaveStartupView
from investors.views_saved import InvestorSavedStartupsList, UnsaveStartupView  # ⬅ додай ці імпорти

router = DefaultRouter()
router.register(r'saved', SavedStartupViewSet, basename='saved-startup')
router.register(r'', InvestorViewSet, basename='investor')

urlpatterns = router.urls + [
    # POST /api/startups/<startup_id>/save/
    path("api/startups/<int:startup_id>/save/", SaveStartupView.as_view(), name="startup-save"),

    # GET /api/investor/saved-startups/
    path("api/investor/saved-startups/", InvestorSavedStartupsList.as_view(), name="investor-saved-startups"),

    # DELETE /api/startups/<startup_id>/unsave/
    path("api/startups/<int:startup_id>/unsave/", UnsaveStartupView.as_view(), name="startup-unsave"),
]