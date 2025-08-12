from django.core.validators import MinValueValidator
from django.db import models

from common.company import Company
from common.enums import Stage


class Investor(Company):
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='investor'
    )
    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.MVP
    )
    fund_size = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        blank=True,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    bookmarks = models.ManyToManyField(
        'startups.Startup',
        through='investors.SavedStartup',
        related_name='bookmarked_by',
        blank=True,
    )

    def clean(self):
        """
        Placeholder for future Investor-specific validation logic.
        """
        super().clean()

        if not self.stage:
            self.stage = Stage.MVP

    def __str__(self):
        return f"{self.company_name} (Investor, User ID: {self.user_id})"

    class Meta:
        db_table = "investors"
        ordering = ["company_name"]
        verbose_name = "Investor"
        verbose_name_plural = "Investors"

class SavedStartup(models.Model):
    investor = models.ForeignKey(
        'investors.Investor',
        on_delete=models.CASCADE,
        related_name='saved_startups',
        db_column='investor_profile_id',
    )
    startup = models.ForeignKey(
        'startups.Startup',
        on_delete=models.CASCADE,
        related_name='saved_by_investors',
        db_column='startup_profile_id',
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ('watching', 'Watching'),
        ('contacted', 'Contacted'),
        ('negotiating', 'Negotiating'),
        ('passed', 'Passed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='watching')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'saved_startups'
        constraints = [
            models.UniqueConstraint(fields=['investor', 'startup'], name='uniq_investor_startup')
        ]
        ordering = ['-saved_at']
        verbose_name = 'Saved Startup'
        verbose_name_plural = 'Saved Startups'

    def __str__(self):
        return f"{self.investor} saved {self.startup}"