import os
import uuid

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings




@csrf_exempt
def upload_and_process(request):
    if request.method == "POST" and request.FILES.get("file"):
        import xarray as xr
        import matplotlib.pyplot as plt  # ⬅️ Lazy import
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

            # ✅ Variable-wise colormaps
            colormaps = {
                "t2": "plasma",       # Temperature
                "rainc": "Blues",     # Rainfall (cumulus)
                "rainnc": "YlGnBu",   # Rainfall (non-cumulus)
                "rh2": "YlGnBu",      # Humidity
                "u10m": "RdBu",       # East-West Wind
                "v10m": "PiYG"        # North-South Wind
            }

            for var in ds.data_vars:
                try:
                    data = ds[var].isel(time=0) if "time" in ds[var].dims else ds[var]
                    cmap = colormaps.get(var.lower(), "viridis")  # fallback cmap

                    plt.figure(figsize=(8, 6))
                    data.plot(cmap=cmap)
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


@csrf_exempt
def upload_and_generate_csv(request):
    if request.method == "POST" and request.FILES.get("file"):
        import xarray as xr
        import pandas as pd

        file = request.FILES["file"]
        filename = f"{uuid.uuid4()}.nc"
        filepath = os.path.join(settings.MEDIA_ROOT, filename)

        with open(filepath, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        try:
            ds = xr.open_dataset(filepath)
            csv_output_dir = os.path.join(settings.MEDIA_ROOT, "csvs")
            os.makedirs(csv_output_dir, exist_ok=True)

            csv_urls = {}  # প্রতিটি variable-এর আলাদা CSV
            merged_df = None  # সব variables মিলিয়ে একটা CSV

            for var in ds.data_vars:
                try:
                    data = ds[var]
                    df = data.to_dataframe().reset_index()

                    # 👉 আলাদা CSV সংরক্ষণ
                    csv_filename = f"{uuid.uuid4()}.csv"
                    csv_path = os.path.join(csv_output_dir, csv_filename)
                    df.to_csv(csv_path, index=False)
                    csv_urls[var] = f"{settings.MEDIA_URL}csvs/{csv_filename}"

                    # 👉 Merge করার জন্য প্রস্তুত
                    df_renamed = df.rename(columns={var: var})
                    if merged_df is None:
                        merged_df = df_renamed
                    else:
                        merged_df = pd.merge(
                            merged_df,
                            df_renamed,
                            on=list(set(df.columns) & set(merged_df.columns)),
                            how="outer",
                        )

                except Exception as e:
                    print(f"Skipping {var}: {e}")

            # 👉 একত্রিত CSV সংরক্ষণ
            combined_csv_url = None
            if merged_df is not None:
                combined_filename = f"{uuid.uuid4()}_combined.csv"
                combined_path = os.path.join(csv_output_dir, combined_filename)
                merged_df.to_csv(combined_path, index=False)
                combined_csv_url = f"{settings.MEDIA_URL}csvs/{combined_filename}"

            return JsonResponse({
                "individual_csvs": csv_urls,
                "combined_csv": combined_csv_url
            })

        except Exception as e:
            return JsonResponse({"error": f"Failed to process file: {str(e)}"}, status=500)

    return JsonResponse({"error": "No file uploaded"}, status=400)
