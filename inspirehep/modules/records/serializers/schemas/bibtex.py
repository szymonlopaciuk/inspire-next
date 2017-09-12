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

"""Marshmallow JSON schema."""

from __future__ import absolute_import, division, print_function

from marshmallow import Schema, post_load
from marshmallow.fields import Str, List, Nested, Int, Date

from inspirehep.modules.records.serializers.fields_export import bibtex_type_and_fields, extractor


class First(List):
    def _deserialize(self, value, attr, data):
        values = super(First, self)._deserialize(value, attr, data)
        if len(values) > 0:
            return values[0]


class AuthorSchema(Schema):
    """Schema for authors in Bibtex references."""
    full_name = Str()

    @post_load
    def make_author(self, data):
        return data['full_name']


class TitleSchema(Schema):
    """Schema for titles in Bibtex references."""
    title = Str()

    @post_load
    def make_title(self, data):
        return data['title']


class InstitutionSchema(Schema):
    """Schema for representing institutions."""
    name = Str()

    @post_load
    def make_institution(self, data):
        return data['name']


class ThesisSchema(Schema):
    """Schema for theses in Bibtex references."""
    degree_type = Str()
    institutions = List(Nested(InstitutionSchema))
    date = Str()  # TODO: Take out the year


class PublicationInfoSchema(Schema):
    """Schema to represent publication_info."""
    journal = Str(load_from='journal_title')
    volume = Str(load_from='journal_volume')
    year = Int()
    number = Str(load_from='journal_issue')
    page_start = Str()
    page_end = Str()


class ValueListSchema(Schema):
    """Schema to represent extract value from an object of the form {value : data}."""
    value = Str()

    @post_load
    def make_value_list(self, obj):
        return obj['value']


class ArXivEprintSchema(Schema):
    """Schema to represent archiv entry objects."""
    categories = List(Str())
    value = Str()


class BibtexSchema(Schema):
    """Schema for Bibtex references."""
    key = Int(load_from='self_recid')
    texkey = First(Str(), load_from='texkeys')
    author = List(Nested(AuthorSchema), load_from='authors')
    title = First(Nested(TitleSchema), load_from='titles')
    document_type = List(Str())
    thesis_info = Nested(ThesisSchema)
    publication_info = First(Nested(PublicationInfoSchema))
    doi = First(Nested(ValueListSchema), load_from='dois')
    arxiv_eprints = First(Nested(ArXivEprintSchema))
    reportNumber = First(Nested(ValueListSchema), load_from='report_numbers')
    preprint_date = Date()
    earliest_date = Date()
    corporate_author = List(Str(), load_from='corporate_authors')
    collaboration = First(Nested(ValueListSchema), load_from='collaborations')

    @post_load
    def make_bibtex(self, data):
        print(str(data))  # TODO: Remove

        doc_type, fields = bibtex_type_and_fields(data)

        template_data = {
            'document_type': doc_type,
            'texkey': data.get('texkey', ''),
            'key': data.get('key')
        }

        for field in fields:
            if field in extractor.store:
                template_data[field] = extractor.store[field](data, doc_type)
            elif field in data:
                template_data[field] = data[field]
            else:
                template_data[field] = None

        return template_data
