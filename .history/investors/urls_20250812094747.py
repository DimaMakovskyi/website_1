from rest_framework.routers import DefaultRouter

from investors.views import InvestorViewSet, SavedStartupViewSet

# Register viewsets with the router
router = DefaultRouter()
router.register(r'', InvestorViewSet, basename='investor')
router.register(r'saved', SavedStartupViewSet, basename='saved-startup')

# Include router-generated URLs
#urlpatterns = [
#    path('', include(router.urls)),
#]
urlpatterns = router.urls