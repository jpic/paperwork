#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012  Jerome Flesch
#    Copyright (C) 2012  Sebastien Maccagnoni-Munch
#
#    Paperwork is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paperwork is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paperwork.  If not, see <http://www.gnu.org/licenses/>.

"""
Code relative to page handling.
"""

import codecs
from copy import copy
import Image
import multiprocessing
import os
import os.path
import re
import threading
import time

from gi.repository import Gtk
import pyocr.builders
import pyocr.pyocr

from paperwork.backend.common.page import BasicPage
from paperwork.backend.common.page import PageExporter
from paperwork.backend.config import PaperworkConfig
from paperwork.util import check_spelling
from paperwork.util import dummy_progress_cb
from paperwork.util import image2surface


class ImgOCRThread(threading.Thread):
    def __init__(self, ocr_tool, langs, imgpath, compute_score=True):
        threading.Thread.__init__(self, name="OCR")
        self.ocr_tool = ocr_tool
        self.langs = langs
        self.imgpath = imgpath
        self.compute_score = compute_score
        self.score = -1
        self.text = None

    def __compute_ocr_score_with_spell_checking(self, txt):
        return check_spelling(self.langs['spelling'], txt)

    @staticmethod
    def __compute_ocr_score_without_spell_checking(txt):
        """
        Try to evaluate how well the OCR worked.
        Current implementation:
            The score is the number of words only made of 4 or more letters
            ([a-zA-Z])
        """
        # TODO(Jflesch): i18n / l10n
        score = 0
        prog = re.compile(r'^[a-zA-Z]{4,}$')
        for word in txt.split(" "):
            if prog.match(word):
                score += 1
        return (txt, score)

    def run(self):
        SCORE_METHODS = [
            ("spell_checker", self.__compute_ocr_score_with_spell_checking),
            ("lucky_guess", self.__compute_ocr_score_without_spell_checking),
            ("no_score", lambda txt: (txt, 0))
        ]

        img = Image.open(self.imgpath)

        print ("Running OCR on '%s'" % self.imgpath)
        self.text = self.ocr_tool.image_to_string(img, lang=self.langs['ocr'])

        if not self.compute_score:
            self.score = 0
            return

        for score_method in SCORE_METHODS:
            try:
                print ("Evaluating score of this page orientation (%s)"
                       " using method '%s' ..."
                       % (self.imgpath, score_method[0]))
                (fixed_text, self.score) = score_method[1](self.text)
                # TODO(Jflesch): For now, we throw away the fixed version:
                # The original version may contain proper nouns, and spell
                # checking could make them disappear
                # However, it would be best if we could keep both versions
                # without increasing too much indexation time
                print "Page orientation score: %d" % self.score
                return
            except Exception, exc:
                print ("**WARNING** Scoring method '%s' failed !"
                       % score_method[0])
                print ("Reason: %s" % (str(exc)))


class ImgPage(BasicPage):
    """
    Represents a page. A page is a sub-element of ImgDoc.
    """
    FILE_PREFIX = "paper."
    ROTATED_FILE_PREFIX = "rotated."
    EXT_TXT = "txt"
    EXT_BOX = "words"
    EXT_IMG_SCAN = "bmp"
    EXT_IMG = "jpg"
    EXT_THUMB = "thumb.jpg"

    KEYWORD_HIGHLIGHT = 3

    ORIENTATION_PORTRAIT = 0
    ORIENTATION_LANDSCAPE = 1

    OCR_THREADS_POLLING_TIME = 0.1

    def __init__(self, doc, page_nb):
        BasicPage.__init__(self, doc, page_nb)

    def __get_filepath(self, ext):
        """
        Returns a file path relative to this page
        """
        return os.path.join(self.doc.path,
                            "%s%d.%s" % (self.FILE_PREFIX,
                                         self.page_nb + 1, ext))

    def __get_box_path(self):
        """
        Returns the file path of the box list corresponding to this page
        """
        return self.__get_filepath(self.EXT_BOX)

    __box_path = property(__get_box_path)

    def __get_img_path(self):
        """
        Returns the file path of the image corresponding to this page
        """
        return self.__get_filepath(self.EXT_IMG)

    __img_path = property(__get_img_path)

    def __get_thumb_path(self):
        """
        Returns the file path of the thumbnail corresponding to this page
        """
        return self.__get_filepath(self.EXT_THUMB)

    __thumb_path = property(__get_thumb_path)

    def __get_last_mod(self):
        try:
            return os.stat(self.__get_box_path()).st_mtime
        except OSError, exc:
            return 0.0

    last_mod = property(__get_last_mod)

    def _get_text(self):
        """
        Get the text corresponding to this page
        """
        boxes = self.boxes
        txt = u""
        for box in boxes:
            txt += u" " + str(box).decode('utf-8')
        return [txt]

    def __get_boxes(self):
        """
        Get all the word boxes of this page.
        """
        boxfile = self.__box_path

        box_builder = pyocr.builders.LineBoxBuilder()

        try:
            with codecs.open(boxfile, 'r', encoding='utf-8') as file_desc:
                boxes = box_builder.read_file(file_desc)
            return boxes
        except IOError, exc:
            print "Unable to get boxes for '%s': %s" % (self.doc.docid, exc)
            return []

    boxes = property(__get_boxes)

    def __get_img(self):
        """
        Returns an image object corresponding to the page
        """
        return Image.open(self.__img_path)

    def __set_img(self, img):
        img.save(self.__img_path)
        self.drop_cache()

    img = property(__get_img, __set_img)

    def __make_thumbnail(self, width):
        """
        Create the page's thumbnail
        """
        img = self.img
        (w, h) = img.size
        factor = (float(w) / width)
        w = width
        h /= factor
        img = img.resize((int(w), int(h)), Image.ANTIALIAS)
        img.save(self.__thumb_path)
        return img

    def __get_thumbnail(self):
        """
        Returns an image object corresponding to the last saved thumbnail
        """
        return Image.open(self.__thumb_path)

    def _get_thumbnail(self, width):
        """
        Returns an image object corresponding to the up-to-date thumbnail
        """
        try:
            if os.path.getmtime(self.__img_path) > \
               os.path.getmtime(self.__thumb_path):
                return self.__make_thumbnail(width)
            else:
                return self.__get_thumbnail()
        except:
            return self.__make_thumbnail(width)

    def __save_imgs(self, img, scan_res=0, scanner_calibration=None,
                    callback=dummy_progress_cb):
        """
        Make a page (on disk), and generate 4 output files:
            <docid>/paper.rotated.0.bmp: original output
            <docid>/paper.rotated.1.bmp: original output at 90 degrees
        OCR will have to decide which is the best
        """
        print "Scanner resolution: %d" % (scan_res)
        print "Scanner calibration: %s" % (str(scanner_calibration))
        print ("Calibration resolution: %d" %
               (PaperworkConfig.CALIBRATION_RESOLUTION))
        if scan_res != 0 and scanner_calibration is not None:
            cropping = (scanner_calibration[0][0]
                        * scan_res
                        / PaperworkConfig.CALIBRATION_RESOLUTION,
                        scanner_calibration[0][1]
                        * scan_res
                        / PaperworkConfig.CALIBRATION_RESOLUTION,
                        scanner_calibration[1][0]
                        * scan_res
                        / PaperworkConfig.CALIBRATION_RESOLUTION,
                        scanner_calibration[1][1]
                        * scan_res
                        / PaperworkConfig.CALIBRATION_RESOLUTION)
            print "Cropping: %s" % (str(cropping))
            img = img.crop(cropping)

        img.load()  # WORKAROUND: For PIL on ArchLinux

        # strip the alpha channel if there is one
        color_channels = img.split()
        img = Image.merge("RGB", color_channels[:3])

        outfiles = []
        # rotate the image 0, 90, 180 and 270 degrees
        for rotation in range(0, 4):
            filename = ("%s%d.%s" % (self.ROTATED_FILE_PREFIX, rotation,
                                     self.EXT_IMG_SCAN))
            imgpath = os.path.join(self.doc.path, filename)
            print ("Saving scan (rotated %d degree) in '%s'"
                   % (rotation * -90, imgpath))
            img.save(imgpath)
            outfiles.append(imgpath)
            img = img.rotate(-90)
        return outfiles

    @staticmethod
    def __compare_score(score_x, score_y):
        """
        Compare scores

        Returns:
            -1 : if X is lower than Y
            1 : if X is higher than Y
            0 : if both are equal
        """
        if score_x < score_y:
            return -1
        elif score_x > score_y:
            return 1
        else:
            return 0

    def __ocr(self, files, langs, callback=dummy_progress_cb):
        """
        Do the OCR on the page
        """

        files = files[:]
        need_scores = len(files) > 1

        callback(0, 100, self.SCAN_STEP_OCR)

        ocr_tools = pyocr.pyocr.get_available_tools()
        if len(ocr_tools) <= 0:
            # shouldn't happen: scan buttons should be disabled
            # in that case
            callback(0, 100, self.SCAN_STEP_OCR)
            raise Exception("No OCR tool available")
        print "Using %s for OCR" % (ocr_tools[0].get_name())

        max_threads = multiprocessing.cpu_count()
        threads = []

        if len(files) > 1:
            print "Will use %d process(es) for OCR" % (max_threads)

        scores = []

        # Run the OCR tools in as many threads as there are processors/core
        # on the computer
        while (len(files) > 0 or len(threads) > 0):
            # look for finished threads
            for thread in threads:
                if not thread.is_alive():
                    threads.remove(thread)
                    scores.append((thread.score, thread.imgpath, thread.text))
                    callback(len(scores),
                             len(scores) + len(files) + len(threads) + 1,
                             self.SCAN_STEP_OCR)
            # start new threads if required
            while (len(threads) < max_threads and len(files) > 0):
                imgpath = files.pop()
                thread = ImgOCRThread(ocr_tools[0], langs, imgpath,
                                      need_scores)
                thread.start()
                threads.append(thread)
            time.sleep(self.OCR_THREADS_POLLING_TIME)

        # We want the higher score first
        scores.sort(cmp=lambda x, y: self.__compare_score(y[0], x[0]))

        print "Best: %f -> %s" % (scores[0][0], scores[0][1])

        print "Extracting boxes ..."
        callback(len(scores), len(scores) + 1, self.SCAN_STEP_OCR)
        builder = pyocr.builders.LineBoxBuilder()
        boxes = ocr_tools[0].image_to_string(Image.open(scores[0][1]),
                                             lang=langs['ocr'],
                                             builder=builder)
        print "Done"

        callback(100, 100, self.SCAN_STEP_OCR)
        return (scores[0][1], scores[0][2], boxes)

    def make(self, img, langs=None, scan_res=0, scanner_calibration=None,
             callback=dummy_progress_cb):
        """
        Scan the page & do OCR
        """
        imgfile = self.__img_path
        boxfile = self.__box_path

        outfiles = self.__save_imgs(img, scan_res, scanner_calibration,
                                    callback)
        if langs is None:
            (bmpfile, txt, boxes) = (outfiles[0], "", [])
        else:
            (bmpfile, txt, boxes) = self.__ocr(outfiles, langs, callback)

        # Convert the image and save it in its final place
        img = Image.open(bmpfile)
        img.save(imgfile)

        # Save the boxes
        with codecs.open(boxfile, 'w', encoding='utf-8') as file_desc:
            pyocr.builders.LineBoxBuilder().write_file(file_desc, boxes)

        # delete temporary files
        for outfile in outfiles:
            os.unlink(outfile)

        print "Scan done"
        self.drop_cache()
        self.doc.drop_cache()

    def print_page_cb(self, print_op, print_context):
        """
        Called for printing operation by Gtk
        """
        SCALING = 2.0

        img = self.img
        (width, height) = img.size

        # take care of rotating the image if required
        if print_context.get_width() <= print_context.get_height():
            print_orientation = self.ORIENTATION_PORTRAIT
        else:
            print_orientation = self.ORIENTATION_LANDSCAPE
        if width <= height:
            img_orientation = self.ORIENTATION_PORTRAIT
        else:
            img_orientation = self.ORIENTATION_LANDSCAPE
        if print_orientation != img_orientation:
            print "Rotating the page ..."
            img = img.rotate(90)

        # scale the image down
        # XXX(Jflesch): beware that we get floats for the page size ...
        new_w = int(SCALING * (print_context.get_width()))
        new_h = int(SCALING * (print_context.get_height()))

        print "DPI: %fx%f" % (print_context.get_dpi_x(),
                              print_context.get_dpi_y())
        print "Scaling it down to %fx%f..." % (new_w, new_h)
        img = img.resize((new_w, new_h), Image.ANTIALIAS)

        surface = image2surface(img)

        # .. and print !
        cairo_context = print_context.get_cairo_context()
        cairo_context.scale(1.0 / SCALING, 1.0 / SCALING)
        cairo_context.set_source_surface(surface, 0, 0)
        cairo_context.paint()

    def redo_ocr(self, langs):
        """
        Rerun the OCR on the document

        Arguments:
            langs --- languages to use with the OCR tool and the spell checker
        """
        print "Redoing OCR of '%s'" % (str(self))

        imgfile = self.__img_path
        boxfile = self.__box_path

        (imgfile, txt, boxes) = self.__ocr([imgfile], langs,
                                           dummy_progress_cb)
        # save the boxes
        with codecs.open(boxfile, 'w', encoding='utf-8') as file_desc:
            pyocr.builders.LineBoxBuilder.write_file(file_desc, boxes)
        self.drop_cache()
        self.doc.drop_cache()

    def __ch_number(self, offset=0, factor=1):
        """
        Move the page number by a given offset. Beware to not let any hole
        in the page numbers when doing this. Make sure also that the wanted
        number is available.
        Will also change the page number of the current object.
        """
        src = {}
        src["box"] = self.__get_box_path()
        src["img"] = self.__get_img_path()
        src["thumb"] = self.__get_thumb_path()

        page_nb = self.page_nb

        page_nb += offset
        page_nb *= factor

        print ("--> Moving page %d (+%d*%d) to index %d"
               % (self.page_nb, offset, factor, page_nb))

        self.page_nb = page_nb

        dst = {}
        dst["box"] = self.__get_box_path()
        dst["img"] = self.__get_img_path()
        dst["thumb"] = self.__get_thumb_path()

        for key in src.keys():
            if os.access(src[key], os.F_OK):
                if os.access(dst[key], os.F_OK):
                    print "Error: file already exists: %s" % dst[key]
                    assert(0)
                os.rename(src[key], dst[key])

    def change_index(self, new_index):
        if (new_index == self.page_nb):
            return

        print "Moving page %d to index %d" % (self.page_nb, new_index)

        # we remove ourselves from the page list by turning our index into a
        # negative number
        page_nb = self.page_nb
        self.__ch_number(offset=1, factor=-1)

        if (page_nb < new_index):
            move = 1
            start = page_nb + 1
            end = new_index + 1
        else:
            move = -1
            start = page_nb - 1
            end = new_index - 1

        print "Moving the other pages: %d, %d, %d" % (start, end, move)
        for page_idx in range(start, end, move):
            page = self.doc.pages[page_idx]
            page.__ch_number(offset=-1*move)

        # restore our index in the positive values,
        # and move it the final index
        diff = new_index - page_nb
        diff *= -1  # our index is temporarily negative
        self.__ch_number(offset=diff+1, factor=-1)

        self.page_nb = new_index

        self.drop_cache()
        self.doc.drop_cache()

    def destroy(self):
        """
        Delete the page. May delete the whole document if it's actually the
        last page.
        """
        print "Destroying page: %s" % self
        if self.doc.nb_pages <= 1:
            self.doc.destroy()
            return
        doc_pages = self.doc.pages[:]
        current_doc_nb_pages = self.doc.nb_pages
        paths = [
            self.__get_box_path(),
            self.__get_img_path(),
            self.__get_thumb_path(),
        ]
        for path in paths:
            if os.access(path, os.F_OK):
                os.unlink(path)
        for page_nb in range(self.page_nb + 1, current_doc_nb_pages):
            page = doc_pages[page_nb]
            page.__ch_number(offset=-1)
        self.drop_cache()
        self.doc.drop_cache()

    def _steal_content(self, other_page):
        """
        Call ImgDoc.steal_page() instead
        """
        other_doc = other_page.doc
        other_doc_pages = other_doc.pages[:]
        other_doc_nb_pages = other_doc.nb_pages
        other_page_nb = other_page.page_nb

        to_move = [
            (other_page.__get_box_path(), self.__get_box_path()),
            (other_page.__get_img_path(), self.__get_img_path()),
            (other_page.__get_thumb_path(), self.__get_thumb_path())
        ]
        for (src, dst) in to_move:
            # sanity check
            if os.access(dst, os.F_OK):
                print "Error, file already exists: %s" % dst
                assert(0)
        for (src, dst) in to_move:
            print "%s --> %s" % (src, dst)
            os.rename(src, dst)

        if (other_doc_nb_pages <= 1):
            other_doc.destroy()
        else:
            for page_nb in range(other_page_nb + 1, other_doc_nb_pages):
                page = other_doc_pages[page_nb]
                page.__ch_number(offset=-1)

        self.drop_cache()
