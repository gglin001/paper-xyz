from __future__ import annotations

import requests


def fetch_ocr_models_via_api(min_downloads=1000, min_likes=50):
    url = "https://huggingface.co/api/models"
    params = {
        # "pipeline_tag": "image-to-text",
        "pipeline_tag": "image-text-to-text",
        "sort": "createdAt",
        "direction": -1,
        "full": "true",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    models = response.json()
    filtered_models = []

    for model in models:
        downloads = model.get("downloads", 0)
        likes = model.get("likes", 0)

        if downloads >= min_downloads and likes >= min_likes:
            filtered_models.append(
                {
                    "model_id": model.get("id"),
                    "created_at": model.get("createdAt"),
                    "downloads": downloads,
                    "likes": likes,
                    "url": f"https://huggingface.co/{model.get('id')}",
                }
            )

    return filtered_models


if __name__ == "__main__":
    results = fetch_ocr_models_via_api(min_downloads=200, min_likes=2)
    for model in results[:]:
        print(
            f"[{model['created_at'][:10]}] {model['model_id']} (⬇️ {model['downloads']} | ❤️ {model['likes']})"
        )
