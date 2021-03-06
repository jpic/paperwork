#!/usr/bin/env python
#    Paperwork - Using OCR to grep dead trees the easy way
#    Copyright (C) 2012  Jerome Flesch
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
Bootstrapping code
"""

import os

import gettext
from gi.repository import GObject
from gi.repository import Gtk
import locale

import pyocr.pyocr
import pyinsane.abstract_th  # Just to start the Sane thread

from frontend import mainwindow
from frontend import workers
from backend.config import PaperworkConfig


LOCALE_PATHS = [
    ('locale/fr/LC_MESSAGES/paperwork.mo', 'locale'),
    ('/usr/local/share/locale/fr/LC_MESSAGES/paperwork.mo',
     '/usr/local/share/locale'),
    ('/usr/share/locale/fr/LC_MESSAGES/paperwork.mo', '/usr/share/locale'),
]


def check_module_version(module_name, module_version, expected_version):
    """
    Check that the specified module is up-to-date enough
    """
    if module_version < expected_version:
        raise Exception(("%s is not up-to-date."
                         " Expected version: %s. Version found: %s")
                        % (module_name, str(expected_version),
                           str(module_version)))


def check_module_versions():
    """
    Check that the required modules are up-to-date enough
    """
    check_module_version("pyocr", pyocr.pyocr.VERSION, (0, 1, 1))


def set_locale():
    """
    Enable locale support
    """
    locale.setlocale(locale.LC_ALL, '')

    got_locales = False
    locales_path = None
    for (fr_locale_path, locales_path) in LOCALE_PATHS:
        print "Looking for locales in '%s' ..." % (fr_locale_path)
        if os.access(fr_locale_path, os.R_OK):
            print "Will use locales from '%s'" % (locales_path)
            got_locales = True
            break
    if not got_locales:
        print "WARNING: Locales not found"
    else:
        for module in (gettext, locale):
            module.bindtextdomain('paperwork', locales_path)
            module.textdomain('paperwork')


def main():
    """
    Where everything start.
    """
    check_module_versions()
    set_locale()

    GObject.threads_init()

    try:
        config = PaperworkConfig()
        config.read()

        main_win = mainwindow.MainWindow(config)
        mainwindow.ActionRebuildIndex(main_win, config).do()
        Gtk.main()
    finally:
        workers.halt()
        print "Good bye"


if __name__ == "__main__":
    main()
