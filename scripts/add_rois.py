import re

import numpy as np
import omero
import omero.cli
from omero.rtypes import rstring
from omero_rois import (masks_from_label_image, mask_from_binary_image)
from skimage.io import imread


RGBA_MASKS = [(0, 255, 0, 130), (0, 0, 255, 130)]
RGBA_MASKS_GT = [(0, 255, 0, 210), (0, 0, 255, 210), (255, 0, 0, 210)]
RGBA_ROI = (255, 0, 255, 130)

def get_paths():
    # /uod/idr/filesets/idr0144-baskay-jawbone/20221019-Globus/idr0000-baskay-3drec/experimentE/PROCESSED/masks/E_22.png
    pattern = re.compile(r".+/(?P<image_type>.+)/(?P<image_name>.+)\.png")
    with open("roi_files.txt", mode='r') as input_file:
        for line in input_file.readlines():
            line = line.strip()
            m = pattern.match(line.strip())
            if m:
                yield (m.group("image_type"), m.group("image_name"), line)


def get_images(conn):
    project = conn.getObject("Project", attributes={"name": "idr0144-baskay-jawbone/experimentA"})
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            yield image


def get_image(conn, image_name):
    project = conn.getObject("Project", attributes={"name": "idr0144-baskay-jawbone/experimentA"})
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            if image.name == f"{image_name}_processed.ome.tiff":
                return image
    print(f"Could not find target image {image.name}")
    return None


def create_rois(path, type):
    roi_img = imread(path, as_gray=True)
    roi_img = roi_img.astype(int)
    rois = []
    if type == "masks":
        labels = np.unique(roi_img)
        for n in range(1, len(labels)):
            mask_data = roi_img == labels[n]
            if n == 1:
                text = "bone graft"
            if n == 2:
                text = "bone tissue"
                mask_data = np.invert(mask_data)
            mask = mask_from_binary_image(mask_data, rgba=RGBA_MASKS[n-1])
            roi = omero.model.RoiI()
            mask.setTextValue(rstring(text))
            roi.addShape(mask)
            rois.append(roi)
    elif type == "roi":
        mask = mask_from_binary_image(roi_img, rgba=RGBA_ROI, text="ROI", raise_on_no_mask=False)
        if mask:
            roi = omero.model.RoiI()
            roi.addShape(mask)
            rois.append(roi)
    elif type == "ground_truth":
        labels = np.unique(roi_img)
        for n in range(1, len(labels)):
            mask_data = roi_img == labels[n]
            if n == 1:
                text = "ground truth - nonmineralized bone graft"
            if n == 2:
                text = "ground truth - mineralizing bone graft"
            if n == 3:
                text = "ground truth - bone tissue"
                mask_data = np.invert(mask_data)
            mask = mask_from_binary_image(mask_data, rgba=RGBA_MASKS_GT[n-1])
            roi = omero.model.RoiI()
            mask.setTextValue(rstring(text))
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


def delete_rois(conn, im):
    result = conn.getRoiService().findByImage(im.id, None)
    to_delete = []
    for roi in result.rois:
        to_delete.append(roi.getId().getValue())
    if to_delete:
        print(f"Deleting existing {len(to_delete)} rois on image {im.name}.")
        conn.deleteObjects("Roi", to_delete, deleteChildren=True, wait=True)


with omero.cli.cli_login() as c:
    conn = omero.gateway.BlitzGateway(client_obj=c.get_client())

    for img in get_images(conn):
        delete_rois(conn, img)

    for type, image, path in get_paths():
        print(path)
        rois = create_rois(path, type)
        img = get_image(conn, image)
        save_rois(conn, img, rois)
