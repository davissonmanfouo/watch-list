from django.db import models

# Create your models here.
class Task(models.Model):
	title = models.CharField(max_length=200)
	complete = models.BooleanField(default=False)
	provider_slug = models.CharField(max_length=50, blank=True, null=True)
	provider_service_id = models.CharField(max_length=20, blank=True, null=True)
	tmdb_series_id = models.PositiveIntegerField(blank=True, null=True)
	created = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=["provider_service_id", "tmdb_series_id"],
				name="unique_provider_series",
			)
		]

	def __str__(self):
		return self.title
