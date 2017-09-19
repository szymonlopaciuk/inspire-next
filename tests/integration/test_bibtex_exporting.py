# -*- coding: utf-8 -*-
#
# This file is part of INSPIRE.
# Copyright (C) 2014-2017 CERN.
#
# INSPIRE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# INSPIRE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with INSPIRE. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

from __future__ import absolute_import, division, print_function

from inspirehep.utils.record_getter import get_es_record

from inspirehep.modules.records.serializers.schemas.bibtex import BibtexSchema
from pybtex.database import Entry, Person


def test_format_article(app):
    article = get_es_record('lit', 4328)
    expected = ("Glashow:1961tr", Entry('article', [
        ('key', '4328'),
        ('journal', u'Nucl.Phys.'),
        ('pages', u'579--588'),
        ('title', u'Partial Symmetries of Weak Interactions'),
        ('volume', u'22'),
        ('year', u'1961'),
        ('doi', u'10.1016/0029-5582(61)90469-2'),
        ('SLACcitation', u"%%CITATION = DOI:10.1016/0029-5582(61)90469-2;%%"),
    ], persons={
        'editor': [],
        'author': [Person(u"Glashow, S.L.")],
    }))

    schema = BibtexSchema()
    result, errors = schema.load(article)

    assert not errors
    assert result == expected


def test_format_inproceeding(app):
    inproceedings = get_es_record('lit', 524480)
    expected = ("Hu:2000az", Entry('inproceedings', [
        ('key', '524480'),
        ('address', u"Tokyo, Japan"),
        ('booktitle', u"4th RESCEU International Symposium on Birth and Evolution of the Universe"),
        ('title', u"CMB anisotropies: A Decadal survey"),
        ('archivePrefix', u'arXiv'),
        ('eprint', u"astro-ph/0002520"),
        ('primaryClass', u"astro-ph"),
        ('SLACcitation', u"%%CITATION = ASTRO-PH/0002520;%%"),
        ('url', u"http://alice.cern.ch/format/showfull?sysnb=2178340"),
    ], persons={
        'editor': [],
        'author': [Person(u"Hu, Wayne")],
    }))

    schema = BibtexSchema()
    result, errors = schema.load(inproceedings)

    assert not errors
    assert result == expected


def test_format_proceeding(app):
    proceedings = get_es_record('lit', 701585)
    expected = ("Alekhin:2005dx", Entry('proceedings', [
        ('key', '701585'),
        ('address', u"Geneva"),
        ('pages', u"pp.1--326"),
        ('publisher', u"CERN"),
        ('title', u"HERA and the LHC: A Workshop on the implications of HERA for LHC physics: Proceedings Part A"),
        ('year', u"2005"),
        ('reportNumber', u"CERN-2005-014, DESY-PROC-2005-01"),
        ('archivePrefix', u"arXiv"),
        ('eprint', u"hep-ph/0601012"),
        ('primaryClass', u"hep-ph"),
        ('SLACcitation', u"%%CITATION = HEP-PH/0601012;%%"),
        ('url', u"http://weblib.cern.ch/abstract?CERN-2005-014"),
    ], persons={
        'editor': [Person(u"De Roeck, A."), Person(u"Jung, H.")],
        'author': [],
    }))

    schema = BibtexSchema()
    result, errors = schema.load(proceedings)

    assert not errors
    assert result == expected


def test_format_phdthesis(app):
    phdthesis = get_es_record('lit', 1395663)
    expected = ("Mankuzhiyil:2010jpa", Entry('phdthesis', [
        ('key', '1395663'),
        ('school', u"Udine U."),
        ('title', u"MAGIC $\\gamma$-ray observations of distant AGN and a study of source variability and the extragalactic background light using FERMI and air Cherenkov telescopes"),
        ('year', u"2010"),
        # ('SLACcitation', u"%%CITATION = INSPIRE-1395663;%%"),
        ('url', u"https://magicold.mpp.mpg.de/publications/theses/NMankuzhiyil.pdf"),
    ], persons={
        'editor': [],
        'author': [Person(u"Mankuzhiyil, Nijil")],
    }))

    schema = BibtexSchema()
    result, errors = schema.load(phdthesis)

    assert not errors
    assert result == expected


def test_format_book(app):
    book = get_es_record('lit', 736770)
    expected = ("Fecko:2006zy", Entry('book', [
        ('key', '736770'),
        ('publisher', u"Cambridge University Press"),
        ('title', u"Differential geometry and Lie groups for physicists"),
        ('year', u"2011"),
        ('isbn', u"9780521187961, 9780521845076, 9780511242960"),
        # ('SLACcitation', u"%%CITATION = INSPIRE-736770;%%"),
    ], persons={
        'editor': [],
        'author': [Person(u"Fecko, M.")],
    }))

    schema = BibtexSchema()
    result, errors = schema.load(book)

    assert not errors
    assert result == expected


def test_format_inbook(app):
    inbook = get_es_record('lit', 1375491)
    expected = ("Bechtle:2015nta", Entry('inbook', [
        ('key', '1375491'),
        ('pages', u"421--462"),
        ('title', u"Supersymmetry"),
        ('year', u"2015"),
        ('doi', u"10.1007/978-3-319-15001-7_10"),
        ('archivePrefix', u"arXiv"),
        ('eprint', u"1506.03091"),
        ('primaryClass', u"hep-ex"),
        ('SLACcitation', u"%%CITATION = ARXIV:1506.03091;%%"),
    ], persons={
        'editor': [],
        'author': [Person(u"Bechtle, Philip"), Person(u"Plehn, Tilman"), Person(u"Sander, Christian")],
    }))

    schema = BibtexSchema()
    result, errors = schema.load(inbook)

    assert not errors
    assert result == expected
