from google.cloud import vision
from pathlib import Path
import cv2
import io
from PIL import Image

def construct_vision_image(image):
    image = vision.Image(content=image)
    return  image

def make_request(image):
    image = construct_vision_image(image)
    client = vision.ImageAnnotatorClient()
    response =client.document_text_detection(image=image)

    return response

def format_text_from_annotations(response,exclusion_zones,y_threshold=10,num_segments=30,x_close_threshold=50):
    items = []
    lines = {}
    table_annotated = {}
    try:
        max_x_coordinate = max(text.bounding_poly.vertices[1].x for text in response.text_annotations[1:])  # Find the maximum x-coordinate
    except Exception as e:
        return ""
    segment_width = max_x_coordinate // num_segments  # Calculate segment width dynamically
    last_bottom_y = 0  # Track the bottom y-coordinate of the last processed line

    # Additional structure to track the last word's x-coordinate in each line
    last_word_x = {}
    def is_within_exclusion_zone(x1, y1, x2, y2):
        for idx,ex_zone in exclusion_zones.items():
            (ex_x1, ex_y1, ex_x2, ex_y2) = ex_zone
            if not (x2 < ex_x1 or x1 > ex_x2 or y2 < ex_y1 or y1 > ex_y2):
                return (True,idx)
        return (False,False)

    for text in response.text_annotations[1:]:
        top_x_axis = text.bounding_poly.vertices[0].x
        top_y_axis = text.bounding_poly.vertices[0].y
        bottom_y_axis = text.bounding_poly.vertices[3].y
        is_present = is_within_exclusion_zone(top_x_axis, top_y_axis, text.bounding_poly.vertices[1].x, bottom_y_axis)
        if is_present[0]:
            if is_present[1] not in table_annotated:
                table_annotated[is_present[1]] = 1
                text.description = len(text.description) * " "
            else:
                if table_annotated[is_present[1]] == 3:
                    text.description = f"# Table_{is_present[1]} is here"
                    table_annotated[is_present[1]] += 1
                else:
                    text.description = len(text.description) * " "
                    table_annotated[is_present[1]] += 1

        # Find an existing line that this text could belong to
        found_line = None
        for s_top_y_axis, s_item in lines.items():
            if abs(s_top_y_axis - top_y_axis) <= y_threshold:
                if top_y_axis < s_item[0][1] + y_threshold:
                    found_line = s_top_y_axis
                    break
        if found_line is None:
            # No suitable line found, create a new line
            lines[top_y_axis] = [(top_y_axis, bottom_y_axis), {}]
            found_line = top_y_axis
            last_word_x[found_line] = 0  # Initialize the last word x-coordinate for this line
        else:
            # Update the bottom_y_axis if necessary
            _, current_bottom_y = lines[found_line][0]
            if bottom_y_axis > current_bottom_y:
                lines[found_line][0] = (top_y_axis, bottom_y_axis)
        # Determine the segment for the text based on the x-coordinate
        segment_index = top_x_axis // segment_width

        # Check if the word is too close to the last word in the same line
        if (top_x_axis - last_word_x[found_line]) < x_close_threshold:
            # Find the segment of the last word in the same line
            for seg_index, words in lines[found_line][1].items():
                if words and words[-1][0] == last_word_x[found_line]:
                    segment_index = seg_index  # Adjust the segment index to the last word's segment
                    break

        if segment_index not in lines[found_line][1]:
            lines[found_line][1][segment_index] = []

        # Add the text to the appropriate segment
        lines[found_line][1][segment_index].append((top_x_axis, text.description))
        last_word_x[found_line] = top_x_axis  # Update the last word x-coordinate for this line

    # Sort and join the texts for each line and segment
    sorted_lines = sorted(lines.items())
    for top_y_axis, item in sorted_lines:
        sorted_segments = sorted(item[1].items())
        full_line = []
        last_segment_end = 0
        for segment_index, words in sorted_segments:
            segment_start = segment_index * segment_width
            if segment_start > last_segment_end and (segment_start - last_segment_end) // 7 > 1:
                full_line.append(' ' * ((segment_start - last_segment_end) // 7))
            sorted_words = sorted(words, key=lambda t: t[0])
            line_text = ' '.join(word for _, word in sorted_words)
            full_line.append(line_text)
            last_segment_end = segment_start + len(line_text) * 7

        items.append((item[0], ''.join(full_line)))

        # Check for large vertical gaps and add an extra line if necessary
        if last_bottom_y and (top_y_axis - last_bottom_y > y_threshold * 2):
            items.append((last_bottom_y + y_threshold, ''))
        last_bottom_y = item[0][1]

    # Combine all lines into a single string
    formatted_text = '\n'.join(item[1] for item in items)
    return formatted_text
