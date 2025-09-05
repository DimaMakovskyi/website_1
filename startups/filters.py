import django_filters as df
from startups.models import Startup

class StartupFilter(df.FilterSet):
    industry = df.CharFilter(field_name="industry__name", lookup_expr="iexact")
    min_team_size = df.NumberFilter(field_name="team_size", lookup_expr="gte")
    funding_needed__lte = df.NumberFilter(field_name="funding_needed", lookup_expr="lte")
    stage = df.CharFilter(field_name="stage", lookup_expr="iexact")
    country = df.CharFilter(field_name="location__country", lookup_expr="iexact")
    city = df.CharFilter(field_name="location__city", lookup_expr="iexact")
    is_verified = df.BooleanFilter(field_name="is_verified")

    class Meta:
        model = Startup
        fields = ["industry","min_team_size","funding_needed__lte","stage","country","city","is_verified"]