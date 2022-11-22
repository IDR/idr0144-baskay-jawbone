
# Will's script to cache the masks
# see https://github.com/IDR/idr0144-baskay-jawbone/issues/1

from datetime import datetime

BASE_URL = "https://idr.openmicroscopy.org/"

project_id = 2501
import requests

project_url = BASE_URL + f"webclient/api/datasets/?id={project_id}"

project_data = requests.get(project_url).json()

print(project_data)

for dataset in project_data["datasets"]:

    imgs_url = BASE_URL + f"webclient/api/images/?id={dataset['id']}"
    imgs_data = requests.get(imgs_url).json()

    for image in imgs_data['images']:

        rois_url = BASE_URL + f"api/v0/m/rois/?image={image['id']}"
        print("rois_url", rois_url)

        rois_data = requests.get(rois_url).json()

        for roi in rois_data['data']:
            for shape in roi['shapes']:
                if shape['@type'].endswith("#Mask"):
                    
                    mask_url = BASE_URL + f"webgateway/render_shape_mask/{shape['@id']}/"
                    print("mask url", mask_url)

                    start = datetime.now()
                    requests.get(mask_url)
                    print("time", datetime.now() - start)


