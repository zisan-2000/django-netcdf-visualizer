import os
import uuid
import xarray as xr
import matplotlib.pyplot as plt

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

@csrf_exempt
def upload_and_process(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]

        # Unique filename
        filename = f"{uuid.uuid4()}.nc"
        filepath = os.path.join(settings.MEDIA_ROOT, filename)

        with open(filepath, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        try:
            ds = xr.open_dataset(filepath)
            output_dir = os.path.join(settings.MEDIA_ROOT, "outputs")
            os.makedirs(output_dir, exist_ok=True)

            image_urls = {}

            for var in ds.data_vars:
                try:
                    data = ds[var].isel(time=0) if "time" in ds[var].dims else ds[var]

                    plt.figure(figsize=(8, 6))
                    data.plot(cmap="viridis")
                    plt.title(var)

                    image_filename = f"{uuid.uuid4()}.png"
                    image_path = os.path.join(output_dir, image_filename)
                    plt.savefig(image_path)
                    plt.close()

                    image_urls[var] = f"{settings.MEDIA_URL}outputs/{image_filename}"

                except Exception as e:
                    print(f"Skipping {var}: {e}")

            return JsonResponse({"images": image_urls})

        except Exception as e:
            return JsonResponse({"error": f"Failed to process file: {str(e)}"}, status=500)

    return JsonResponse({"error": "No file uploaded"}, status=400)
