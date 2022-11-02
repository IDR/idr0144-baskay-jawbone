import re

import omero
from omero.rtypes import rstring
from omero_rois import (masks_from_label_image, mask_from_binary_image)
from skimage.io import imread


RGBA_MASKS = (128, 128, 128, 180)
RGBA_ROI = (128, 0, 128, 180)

def get_paths():
    # /uod/idr/filesets/idr0144-baskay-jawbone/20221019-Globus/idr0000-baskay-3drec/experimentE/PROCESSED/masks/E_22.png
    pattern = re.compile(r".+/(?P<image_type>.+)/(?P<image_name>.+)\.png")
    with open("roi_files.txt", mode='r') as input_file:
        for line in input_file.readlines():
            m = pattern.match(line.strip())
            if m:
                yield (m.group("image_type"), m.group("image_name"), line)


def get_image(conn, image_name):
    project = conn.getObject("Project", attributes={"name": "idr0144-baskay-jawbone/experimentA"})
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            if image.name == f"{image_name}_processed.ome.tiff":
                return image
    print(f"Could not find target image {image.name}")
    return None


def create_rois(path, type):
    roi_img = imread(path)
    rois = []
    if type == "masks":
        masks = masks_from_label_image(roi_img, rgba=RGBA_MASKS, raise_on_no_mask=False)
        for i, mask in enumerate(masks):
            roi = omero.model.RoiI()
            roi.setName(rstring(i))
            roi.addShape(mask)
            rois.append(roi)
    elif type == "roi":
        mask = mask_from_binary_image(roi_img, rgba=RGBA_ROI, raise_on_no_mask=False)
        if mask:
            roi = omero.model.RoiI()
            roi.setName(rstring("ROI"))
            roi.addShape(mask)
            rois.append(roi)
    else:
        print("Not implemented")
    return rois


def save_rois(conn, im, rois):
    print('Saving %d ROIs for image %d:%s' % (len(rois), im.id, im.name))
    us = conn.getUpdateService()
    for roi in rois:
        im = conn.getObject('Image', im.id)
        roi.setImage(im._obj)
        us.saveAndReturnObject(roi)


with omero.cli.cli_login() as c:
    conn = omero.gateway.BlitzGateway(client_obj=c.get_client())
    for type, image, path in get_paths():
        rois = create_rois(path, type)
        img = get_image(conn, image)
        save_rois(conn, img, rois)
