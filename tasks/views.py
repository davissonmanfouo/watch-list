import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import TaskForm
from .models import Task

TMDB_DISCOVER_TV_URL = "https://api.themoviedb.org/3/discover/tv"
STREAMING_PROVIDERS = {
    "netflix": {"id": "8", "label": "Netflix"},
    "amazon-prime": {"id": "9", "label": "Amazon Prime Video"},
    "apple-tv": {"id": "350", "label": "Apple TV"},
}


def index(request):
    tasks = Task.objects.all()
    form = TaskForm()

    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            # Adds to the database if valid.
            form.save()
        return redirect("/")

    context = {"tasks": tasks, "form": form}
    return render(request, "tasks/list.html", context)


def _fetch_top_rated_series(provider_id, limit=10, excluded_series_ids=None):
    token = getattr(settings, "TMDB_READ_ACCESS_TOKEN", "")
    language = getattr(settings, "TMDB_LANGUAGE", "fr-FR")
    watch_region = getattr(settings, "TMDB_WATCH_REGION", "US")

    if not token:
        raise ValueError("TMDB_READ_ACCESS_TOKEN is not configured.")

    excluded_ids = set(excluded_series_ids or [])
    collected_series = []
    page = 1
    total_pages = 1

    while len(collected_series) < limit and page <= total_pages:
        params = {
            "language": language,
            "page": page,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 500,
            "watch_region": watch_region,
            "with_watch_monetization_types": "flatrate",
            "with_watch_providers": provider_id,
        }
        request = Request(
            f"{TMDB_DISCOVER_TV_URL}?{urlencode(params)}",
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )

        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        total_pages = int(payload.get("total_pages", 1) or 1)
        results = payload.get("results", [])
        for item in results:
            series_id = item.get("id")
            series_name = item.get("name")
            if not series_id or not series_name:
                continue
            if series_id in excluded_ids:
                continue

            excluded_ids.add(series_id)
            collected_series.append({"id": series_id, "name": series_name})
            if len(collected_series) == limit:
                break

        page += 1

    return collected_series


@require_POST
def addProviderWatchlist(request, provider_slug):
    provider = STREAMING_PROVIDERS.get(provider_slug)
    if provider is None:
        messages.error(request, "Plateforme non supportee.")
        return redirect("list")

    existing_provider_series_ids = set(
        Task.objects.filter(provider_service_id=provider["id"])
        .exclude(tmdb_series_id__isnull=True)
        .values_list("tmdb_series_id", flat=True)
    )

    try:
        series_items = _fetch_top_rated_series(
            provider["id"],
            limit=10,
            excluded_series_ids=existing_provider_series_ids,
        )
    except ValueError:
        messages.error(
            request,
            "TMDB_READ_ACCESS_TOKEN manquant. Configurez cette variable d'environnement.",
        )
        return redirect("list")
    except HTTPError as exc:
        if exc.code == 401:
            messages.error(
                request,
                "TMDB a refuse la requete (401). Verifiez votre Read Access Token.",
            )
        else:
            messages.error(
                request,
                f"TMDB a retourne une erreur HTTP ({exc.code}).",
            )
        return redirect("list")
    except URLError:
        messages.error(
            request,
            "Impossible de contacter TMDB (probleme reseau).",
        )
        return redirect("list")
    except TimeoutError:
        messages.error(
            request,
            "TMDB ne repond pas (timeout).",
        )
        return redirect("list")
    except json.JSONDecodeError:
        messages.error(
            request,
            "Reponse TMDB invalide. Reessayez dans quelques secondes.",
        )
        return redirect("list")

    created_count = 0
    for item in series_items:
        task_title = f"[{provider['label']}] {item['name']}"
        _, created = Task.objects.get_or_create(
            provider_service_id=provider["id"],
            tmdb_series_id=item["id"],
            defaults={
                "title": task_title,
                "complete": False,
                "provider_slug": provider_slug,
            },
        )
        if created:
            created_count += 1

    if created_count:
        messages.success(
            request,
            f"{created_count} series {provider['label']} ajoutees a votre watchlist.",
        )
    else:
        messages.info(request, f"Aucune nouvelle serie {provider['label']} a ajouter.")

    return redirect("list")


def updateTask(request, pk):
    task = Task.objects.get(id=pk)
    form = TaskForm(instance=task)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect("/")

    context = {"form": form}
    return render(request, "tasks/update_task.html", context)


def deleteTask(request, pk):
    item = Task.objects.get(id=pk)

    if request.method == "POST":
        item.delete()
        return redirect("/")

    context = {"item": item}
    return render(request, "tasks/delete.html", context)
