import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from tasks.models import Task
from tasks.forms import TaskForm


class TaskModelTest(TestCase):
    """Tests liés au modèle Task"""

    def test_task_creation_defaults(self):
        task = Task.objects.create(title="Test task")

        self.assertEqual(task.title, "Test task")
        self.assertFalse(task.complete)
        self.assertIsNotNone(task.created)

    def test_task_str_representation(self):
        task = Task.objects.create(title="Ma tâche")
        self.assertEqual(str(task), "Ma tâche")


class TaskFormTest(TestCase):
    """Tests du formulaire TaskForm"""

    def test_task_form_valid(self):
        form = TaskForm(data={
            "title": "Nouvelle tâche",
            "complete": False
        })
        self.assertTrue(form.is_valid())

    def test_task_form_invalid_without_title(self):
        form = TaskForm(data={
            "complete": False
        })
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)


class TaskUrlsTest(TestCase):
    """Tests de résolution des URLs"""

    def test_index_url_accessible(self):
        response = self.client.get(reverse("list"))
        self.assertEqual(response.status_code, 200)


class TaskViewsTest(TestCase):
    """Tests des vues"""

    def setUp(self):
        self.task = Task.objects.create(title="Task initiale")

    def test_index_view_lists_tasks(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task initiale")

    def test_create_task_via_post(self):
        response = self.client.post("/", {
            "title": "Task POST",
            "complete": False
        })

        self.assertEqual(Task.objects.count(), 2)
        self.assertRedirects(response, "/")

    def test_update_task_get(self):
        response = self.client.get(f"/update_task/{self.task.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task initiale")

    def test_update_task_post(self):
        response = self.client.post(
            f"/update_task/{self.task.id}/",
            {
                "title": "Task modifiée",
                "complete": True
            }
        )

        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Task modifiée")
        self.assertTrue(self.task.complete)
        self.assertRedirects(response, "/")

    def test_delete_task_get(self):
        response = self.client.get(f"/delete_task/{self.task.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task initiale")

    def test_delete_task_post(self):
        response = self.client.post(f"/delete_task/{self.task.id}/")

        self.assertEqual(Task.objects.count(), 0)
        self.assertRedirects(response, "/")

    def test_add_watchlist_provider_requires_post(self):
        response = self.client.get(
            reverse("add_watchlist_provider", kwargs={"provider_slug": "netflix"})
        )
        self.assertEqual(response.status_code, 405)

    def test_add_watchlist_provider_invalid_slug(self):
        response = self.client.post(
            reverse("add_watchlist_provider", kwargs={"provider_slug": "invalid"})
        )
        self.assertRedirects(response, "/")

    def _assert_watchlist_import(self, provider_slug, label, provider_id):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        payload = {
            "results": [{"id": index, "name": f"Serie {index}"} for index in range(1, 11)],
            "total_pages": 1,
        }
        with patch("tasks.views.urlopen") as mocked_urlopen:
            mocked_urlopen.return_value = FakeResponse(payload)
            response = self.client.post(
                reverse("add_watchlist_provider", kwargs={"provider_slug": provider_slug})
            )

        self.assertRedirects(response, "/")
        self.assertEqual(Task.objects.filter(title__startswith=f"[{label}]").count(), 10)
        self.assertIn(f"with_watch_providers={provider_id}", mocked_urlopen.call_args[0][0].full_url)
        self.assertEqual(
            Task.objects.filter(provider_service_id=provider_id, tmdb_series_id__isnull=False).count(),
            10,
        )

    @override_settings(
        TMDB_READ_ACCESS_TOKEN="token",
        TMDB_LANGUAGE="fr-FR",
        TMDB_WATCH_REGION="US",
    )
    def test_add_netflix_watchlist_creates_10_tasks(self):
        self._assert_watchlist_import("netflix", "Netflix", "8")

    @override_settings(
        TMDB_READ_ACCESS_TOKEN="token",
        TMDB_LANGUAGE="fr-FR",
        TMDB_WATCH_REGION="US",
    )
    def test_add_amazon_watchlist_creates_10_tasks(self):
        self._assert_watchlist_import("amazon-prime", "Amazon Prime Video", "9")

    @override_settings(
        TMDB_READ_ACCESS_TOKEN="token",
        TMDB_LANGUAGE="fr-FR",
        TMDB_WATCH_REGION="US",
    )
    def test_add_apple_watchlist_creates_10_tasks(self):
        self._assert_watchlist_import("apple-tv", "Apple TV", "350")

    @override_settings(
        TMDB_READ_ACCESS_TOKEN="token",
        TMDB_LANGUAGE="fr-FR",
        TMDB_WATCH_REGION="US",
    )
    def test_double_click_netflix_adds_20_distinct_series(self):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(request, timeout=10):
            parsed = urlparse(request.full_url)
            query = parse_qs(parsed.query)
            page = int(query.get("page", ["1"])[0])

            if page == 1:
                results = [{"id": index, "name": f"Netflix Serie {index}"} for index in range(1, 11)]
                payload = {"results": results, "total_pages": 2}
            elif page == 2:
                results = [{"id": index, "name": f"Netflix Serie {index}"} for index in range(11, 21)]
                payload = {"results": results, "total_pages": 2}
            else:
                payload = {"results": [], "total_pages": 2}

            return FakeResponse(payload)

        with patch("tasks.views.urlopen", side_effect=fake_urlopen):
            response_first = self.client.post(
                reverse("add_watchlist_provider", kwargs={"provider_slug": "netflix"})
            )
            response_second = self.client.post(
                reverse("add_watchlist_provider", kwargs={"provider_slug": "netflix"})
            )

        self.assertRedirects(response_first, "/")
        self.assertRedirects(response_second, "/")
        self.assertEqual(Task.objects.filter(provider_service_id="8").count(), 20)
        self.assertEqual(
            Task.objects.filter(provider_service_id="8").values("tmdb_series_id").distinct().count(),
            20,
        )
