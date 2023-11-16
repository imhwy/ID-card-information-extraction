# import libraries
import os
from typing import Optional
import numpy as np
import yolov5
from PIL import Image
from vietocr.tool.config import Cfg
from vietocr.tool.predictor import Predictor
import sources.Controllers.config as cfg
from sources.Controllers import utils
import json


def extract_info(img_path, CORNER_MODEL, CONTENT_MODEL, SAVE_DIR, detector):
    img = Image.open(img_path)
    CORNER = CORNER_MODEL(img)
    predictions = CORNER.pred[0]
    categories = predictions[:, 5].tolist()
    if len(categories) != 4:
        return "Detecting corner failed!"
    boxes = utils.class_Order(
        predictions[:, :4].tolist(), categories)
    center_points = list(map(utils.get_center_point, boxes))
    c2, c3 = center_points[2], center_points[3]
    c2_fix, c3_fix = (c2[0], c2[1] + 30), (c3[0], c3[1] + 30)
    center_points = [center_points[0], center_points[1], c2_fix, c3_fix]
    center_points = np.asarray(center_points)
    aligned = utils.four_point_transform(img, center_points)
    # Convert from OpenCV to PIL format
    aligned = Image.fromarray(aligned)
    CONTENT = CONTENT_MODEL(aligned)
    predictions = CONTENT.pred[0]
    categories = predictions[:, 5].tolist()
    if 7 not in categories:
        if len(categories) < 9:
            return "Missing fields! Detecting content failed!"
    elif 7 in categories:
        if len(categories) < 10:
            return "issing fields! Detecting content failed!"

    boxes = predictions[:, :4].tolist()
    boxes, categories = utils.non_max_suppression_fast(
        np.array(boxes), categories, 0.7)
    boxes = utils.class_Order(boxes, categories)  # x1, x2, y1, y2
    if not os.path.isdir(SAVE_DIR):
        os.mkdir(SAVE_DIR)
    else:
        for f in os.listdir(SAVE_DIR):
            os.remove(os.path.join(SAVE_DIR, f))
    for index, box in enumerate(boxes):
        left, top, right, bottom = box
        if 5 < index < 9:
            # right = c3[0]
            right = right + 100
        cropped_image = aligned.crop((left, top, right, bottom))
        cropped_image = cropped_image.convert('RGB')
        cropped_image.save(os.path.join(SAVE_DIR, f"{index}.jpg"))
    FIELDS_DETECTED = []  # Collecting all detected parts
    for idx, img_crop in enumerate(sorted(os.listdir(SAVE_DIR))):
        if idx > 0:
            img_ = Image.open(os.path.join(SAVE_DIR, img_crop))
            s = detector.predict(img_)
            FIELDS_DETECTED.append(s)

    if 7 in categories:
        FIELDS_DETECTED = (
            FIELDS_DETECTED[:6]
            + [FIELDS_DETECTED[6] + ", " + FIELDS_DETECTED[7]]
            + [FIELDS_DETECTED[8]]
        )
    return FIELDS_DETECTED


def main():
    # Init yolov5 model
    CORNER_MODEL = yolov5.load(cfg.CORNER_MODEL_PATH)
    CONTENT_MODEL = yolov5.load(cfg.CONTENT_MODEL_PATH)

    # Set conf and iou threshold -> Remove overlap and low confident bounding boxes
    CONTENT_MODEL.conf = cfg.CONF_CONTENT_THRESHOLD
    CONTENT_MODEL.iou = cfg.IOU_CONTENT_THRESHOLD

    # Config directory
    SAVE_DIR = cfg.SAVE_DIR

    """ Recognizion detected parts in ID """
    config = Cfg.load_config_from_name(
        "vgg_seq2seq"
    )  # OR vgg_transformer -> acc || vgg_seq2seq -> time
    # config = Cfg.load_config_from_file(cfg.OCR_CFG)
    # config['weights'] = cfg.OCR_MODEL_PATH
    config["cnn"]["pretrained"] = False
    config["device"] = cfg.DEVICE
    config["predictor"]["beamsearch"] = False
    detector = Predictor(config)

    img_path = "C:/UIT/HK5-III/Advanced-computer-vision-CS331.O11/lab/idcard/test.jpg"
    result = extract_info(img_path, CORNER_MODEL,
                          CONTENT_MODEL, SAVE_DIR, detector)
    info = {'ID': result[0],
            'Full name': result[1],
            'Date of birth': result[2],
            'Sex': result[3],
            'Nationality': result[4],
            'Place of origin': result[5],
            'Place of residence': result[6],
            'Date of expiry': result[7]}

    with open('test.json', 'w', encoding='utf-8') as output_file:
        json.dump(info, output_file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
