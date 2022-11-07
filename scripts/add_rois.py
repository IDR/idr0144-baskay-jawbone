import re

import numpy as np
import omero
import omero.cli
from omero.rtypes import rstring
from omero_rois import (masks_from_label_image, mask_from_binary_image)
from skimage.io import imread


# Color for the masks
RGBA_MASKS = [(0, 255, 0, 120), (0, 0, 255, 120)]

# Color for the ground truth masks
RGBA_MASKS_GT = [(0, 255, 0, 210), (0, 0, 255, 210), (255, 0, 0, 210)]

# Color for the Roi
RGBA_ROI = (255, 0, 255, 130)


def get_paths():
    """
    Process the roi files list.
    :return: Tuple (image_type, image_name, file path)
    where image_type == 'masks' || 'roi' || 'ground_truth'
    """
    # /uod/idr/filesets/idr0144-baskay-jawbone/20221019-Globus/idr0000-baskay-3drec/experimentE/PROCESSED/masks/E_22.png
    pattern = re.compile(r".+/(?P<image_type>.+)/(?P<image_name>.+)\.png")
    with open("roi_files.txt", mode='r') as input_file:
        for line in input_file.readlines():
            line = line.strip()
            m = pattern.match(line.strip())
            if m:
                yield (m.group("image_type"), m.group("image_name"), line)


def get_images(conn):
    """
    Get all images of the idr0144 project
    :param conn: omero connection
    :return: Generator
    """
    project = conn.getObject("Project", attributes={"name": "idr0144-baskay-jawbone/experimentA"})
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            yield image


def get_image(conn, image_name):
    """
    Get a particular image of project idr0144
    :param conn: omero connection
    :param image_name: Name of the image
    :return:
    ImageWrapper or None
    """
    project = conn.getObject("Project", attributes={"name": "idr0144-baskay-jawbone/experimentA"})
    for dataset in project.listChildren():
        for image in dataset.listChildren():
            if image.name == f"{image_name}.ome.tiff":
                return image
    print(f"Could not find target image {image.name}")
    return None


def create_rois(path, type):
    """
    Create ROIs from the given image
    :param path: Path to the image
    :param type: Type of the image ('masks' || 'roi' || 'ground_truth')
    :return: List of ROIs
    """
    roi_img = imread(path, as_gray=True)
    roi_img = roi_img.astype(int)
    rois = []
    if type == "masks":
        labels = np.unique(roi_img)
        assert len(labels) == 3 # two masks + background
        for n in range(0, 2):  # skip 2 (background)
            mask_data = roi_img == labels[n]
            if n == 0:
                text = "bone tissue"
            if n == 1:
                text = "bone graft"
            mask = mask_from_binary_image(mask_data, rgba=RGBA_MASKS[n])
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
        assert len(labels) == 4 # three masks + background
        for n in range(0, 3): # skip 3 (background)
            mask_data = roi_img == labels[n]
            if n == 0:
                text = "ground truth - bone tissue"
            if n == 1:
                text = "ground truth - nonmineralized bone graft"
            if n == 2:
                text = "ground truth - mineralizing bone graft"
            mask = mask_from_binary_image(mask_data, rgba=RGBA_MASKS_GT[n])
            roi = omero.model.RoiI()
            mask.setTextValue(rstring(text))
            roi.addShape(mask)
            rois.append(roi)
    else:
        print("Not implemented")
    return rois


def save_rois(conn, im, rois):
    """
    Saves the ROIs to the given image
    :param conn: omero connection
    :param im:  The image
    :param rois: List of ROIs
    :return: Nothing
    """
    print('Saving %d ROIs for image %d:%s' % (len(rois), im.id, im.name))
    us = conn.getUpdateService()
    for roi in rois:
        im = conn.getObject('Image', im.id)
        roi.setImage(im._obj)
        us.saveAndReturnObject(roi)


def delete_rois(conn, im):
    """
    Delete all ROIs attached to the given image
    :param conn: omero connection
    :param im: The image
    :return: Nothing
    """
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
