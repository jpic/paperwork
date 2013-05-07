# Paperwork


## Description

Paperwork is a tool to make papers searchable.

The basic idea behind Paperwork is "scan & forget" : You should be able to just
scan a new document and forget about it until the day you need it again. Let the
machine do most of the work.


## Screenshots

### Main window

<a href="http://jflesch.kwain.net/~jflesch/paperwork/paperwork.alpha.main_window.png">
  <img src="http://jflesch.kwain.net/~jflesch/paperwork/paperwork.alpha.main_window.png" width="512" height="384" />
</a>

### Search suggestions

<a href="http://jflesch.kwain.net/~jflesch/paperwork/paperwork.alpha.suggestions.png">
  <img src="http://jflesch.kwain.net/~jflesch/paperwork/paperwork.alpha.suggestions.png" width="512" height="384" />
</a>

### Labels

<a href="http://jflesch.kwain.net/~jflesch/paperwork/paperwork.alpha.multiple_labels.png">
  <img src="http://jflesch.kwain.net/~jflesch/paperwork/paperwork.alpha.multiple_labels.png" width="402" height="358" />
</a>

<a href="http://jflesch.kwain.net/~jflesch/paperwork/paperwork.alpha.label_edit.png">
  <img src="http://jflesch.kwain.net/~jflesch/paperwork/paperwork.alpha.label_edit.png" width="512" height="384" />
</a>

### Settings window

<a href="http://jflesch.kwain.net/~jflesch/paperwork/paperwork.alpha.settings.png">
  <img src="http://jflesch.kwain.net/~jflesch/paperwork/paperwork.alpha.settings.png" width="512" height="384" />
</a>


## Details

Papers are organized into documents. Each document contains pages.

It uses mainly 3 other pieces of software:

* Sane: To scan the pages
* Cuneiform or Tesseract: To extract the words from the pages (OCR)
* GTK/Glade: For the user interface

Page orientation is automatically guessed using OCR.

Paperwork uses a custom indexation system to search documents and to provide
keyword suggestions. Since OCR is not perfect, and since some documents don't
contain useful keywords, Paperwork allows also to put labels on each document.


## Licence

GPLv3. See COPYING.


## Dependencies

* python v2.7<br/>
  Paperwork is written for Python **2.7**.
  So depending of your Linux distribution, you may have to invoke "python2"
  instead of "python" (for instance with Arch Linux)
* pygi (required):
    * Debian/Ubuntu package: python-gi
* gtk v3 (required)
	* Debian/Ubuntu package: gir1.2-gtk-3.0
* gladeui (required)
	* Debian/Ubuntu package: gir1.2-gladeui-2.0
* pycountry (required)
	* Debian/Ubuntu package: python-pycountry
* python-imaging (aka PIL) (required)
	* Debian/Ubuntu package: python-imaging
* poppler (required)
	* Debian/Ubuntu package: gir1.2-poppler-0.18
* Python Cairo bindings for the GObject library (required):
	* Debian/Ubuntu package: python-gi-cairo
* python-enchant (required)
	* Debian/Ubuntu package: python-enchant
* python-levenshtein (required)
	* Debian/Ubuntu package: python-levenshtein
* python-whoosh (required)
	* Debian/Ubuntu package: python-whoosh
* pyinsane (required)
	* Debian/Ubuntu package: none at the moment
	* Manual installation:
		* git clone git://github.com/jflesch/pyinsane.git
		* cd pyinsane
		* sudo python ./setup.py install
	* Or just this with either sudo or virtualenv:
		* pip install -e git+git://github.com/jflesch/pyinsane.git#egg=pyinsane
* OCR (optional for document searching ; required for scanning)
	* Tesseract (>= v3.01) (recommended)
		* Debian/Ubuntu package: tesseract-ocr tesseract-ocr-&lt;your language&gt;
	* **Or** Cuneiform (>= v1.1)
    	* Debian/Ubuntu package: cuneiform
* pyocr (required)
	* Debian/Ubuntu package: none at the moment
	* Manual installation:
		* git clone git://github.com/jflesch/pyocr.git
		* cd pyocr
		* sudo python ./setup.py install
	* Or just this with either sudo or virtualenv:
		* pip instal -e git+git://github.com/jflesch/pyocr.git#egg=pyocr

## Installation

	$ git clone git://github.com/jflesch/paperwork.git
	$ cd paperwork
	$ sudo python ./setup.py install
	$ paperwork

Enjoy :-)


## Contact

* Mailing-list: [paperwork-gui@googlegroups.com](https://groups.google.com/d/forum/paperwork-gui)
* Bug tracker: [https://github.com/jflesch/paperwork/issues](https://github.com/jflesch/paperwork/issues)


## Development

See [the hacking guide](HACKING.markdown#HACKING)
