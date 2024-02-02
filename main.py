#!/usr/bin/env python3

#
# This code is licensed under the terms of "The Unlicense" license. For more information, please see the LICENSE file contained in this repository alongside the code or refer to <https://unlicense.org>
#

import cv2
import math
import argparse
import pathlib
from collections import namedtuple, OrderedDict

Point = namedtuple("Point", "x y")
Image = namedtuple("Image", "path chx chy")
Brackets = namedtuple("Brackets", "open close")
Chunk = namedtuple("Chunk", "name data")

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("i", help="input directory or image")  # input
    parser.add_argument("o", help="output directory")  # output
    parser.add_argument("-v", "--verbose", help="see more details when program is running",
                        action="store_true")  # verbose
    parser.add_argument("-g", "--group_size", type=int, choices=range(1, 11), default=2, help="change the number of displays per file (1 to 10)")  # group size 1 to 10 (included)
    parser.add_argument("-c", "--add_code", help="add some code to make copypasting easier",
                        action="store_true")  # add code
    parser.add_argument("-f", "--one_file", help="store in just 1 file",
                        action="store_true")  # store in 1 file
    parser.add_argument("--overwrite", help="overwrite existing files",
                        action="store_true")  # overwrite
    args = parser.parse_args()
    return args


def check_path(inpt, output, v=False):
    exit_msg = ""
    if not inpt.exists():
        exit_msg += "Invalid input path (Must be a valid file/directory)"
    if not output.is_dir():
        if exit_msg: exit_msg += "\n"
        exit_msg += "Invalid output path (Must be a valid directory)"
    if exit_msg: raise SystemExit(exit_msg)
    if v: print("Path check successful (paths exist and fulfill file/dir conditions)")


def get_image_tuples(path, chunk_size=Point(16, 16), extensions=[".jpg", ".jpeg", ".png", ".bmp", ".tiff"], v=False):
    class NotAnImage(Exception):
        """An exception for non-images that give an array of size 0 when processed by cv2.imread"""

    class TooSmallImage(Exception):
        """An exception for images smaller than 1 chunk"""

    image_paths = []
    image_tuples = []
    if path.is_file() and path.suffix in extensions:
        image_paths.append(path)
    elif path.is_dir():
        image_paths = [child for child in sorted(path.iterdir()) if child.is_file() and child.suffix in extensions]
    if not image_paths: raise SystemExit("No suitable files found in input path")
    for image in image_paths:
        try:
            img = cv2.imread(str(image), cv2.IMREAD_COLOR)
            if img.size == 0: raise NotAnImage()
            vertical_ch, horizontal_ch = math.floor(img.shape[0] / chunk_size.y), math.floor(
                img.shape[1] / chunk_size.x)
            if not (vertical_ch and horizontal_ch): raise TooSmallImage()
            image_tuples.append(Image(image, horizontal_ch, vertical_ch))
            if v: print(f"Succesfully read image: {image}")
        except NotAnImage:
            print(f"Failed to read image (not an image or corrupted): {image}")
            continue
        except TooSmallImage:
            print(f"Can't process image (smaller than chunk size): {image}")
            continue
        except Exception as err:
            print(err)
            continue
    return image_tuples


def get_chunks_dict(img, chunk_size, v=False):
    image = cv2.imread(str(img.path), cv2.IMREAD_COLOR)
    chunks_dict = OrderedDict(
        (
            ((ch_column, ch_row),
            [
                [
                    "#{0:02x}{1:02x}{2:02x}".format(
                                            *image[y + ch_row * chunk_size.y, x + ch_column * chunk_size.x,][::-1])
                    for x in range(chunk_size.x)
                ]
                for y in range(chunk_size.y)
            ]
            )
            for ch_row in range(img.chy) for ch_column in range(img.chx)
        )
    )
    if v: print(f"Successfully processed image: {img.path}")
    return chunks_dict


def output_generator(chunks_dict, chunks_group_size=1, brackets=Brackets("{", "}")):
    for i in range(0, len(chunks_dict), chunks_group_size):
        yield Chunk(str(list(chunks_dict.keys())[i:i + chunks_group_size]).replace("[", "").replace("]", ""),
              str(list(chunks_dict.values())[i:i + chunks_group_size]) \
              .replace("[", brackets.open).replace("]", brackets.close)), int(i/chunks_group_size)


def store_output(header, data, img, output_dir, num=0, one_file=False, overwrite=False, add_code=False, v=False):
    output_file = pathlib.Path.joinpath(output_dir, f"{img.path.stem}[{img.chx},{img.chy}]")
    if not one_file: output_file = pathlib.Path.with_name(output_file, output_file.stem + f"({num})")
    output_file = pathlib.Path.with_name(output_file, output_file.name + ".txt")
    mode = "a" if output_file.exists() and (not overwrite or one_file) else "w"
    if overwrite and num == 0:
        with open(output_file, "w", encoding="utf-8") as fh: fh.write("")
    front_code = "mem.data = " if add_code else ""
    back_code = "\nfor k,v in ipairs({" + f"{header}".replace("(", '"').replace(")", '"').replace(" ", "") + "}) do digiline_send(v, mem.data[k]) end\n" if add_code else ""
    with open(output_file, mode, encoding="utf-8") as fh:
        fh.write(f"--{header}\n\n{front_code}{data}\n{back_code}\n")
    if v: print(f"Successfully stored image: {img.path}, chunks {header} as {output_file}")


def main():
    default_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
    args = get_args()
    i, o = pathlib.Path(args.i), pathlib.Path(args.o)
    v, g, c, f, overwrite = args.verbose, args.group_size, args.add_code, args.one_file, args.overwrite
    chunk_size = Point(16, 16)
    chunks_group_size = args.group_size
    check_path(i, o, v)
    image_tuples = get_image_tuples(i, chunk_size, extensions=default_extensions, v=v)
    for img in image_tuples:
        chunks_dict = get_chunks_dict(img, chunk_size, v=v)
        for chunk_group, num in output_generator(chunks_dict, chunks_group_size=g):
            store_output(header=chunk_group.name, data=chunk_group.data, num=num, img=img, add_code=c, one_file=f, overwrite=overwrite, output_dir=o, v=v)
    print("Program finished")


if __name__ == "__main__":
    main()