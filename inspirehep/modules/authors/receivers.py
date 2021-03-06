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

import uuid

from flask import current_app

from invenio_indexer.signals import before_record_index
from invenio_records.signals import (
    before_record_insert,
    before_record_update,
)

from .utils import author_tokenize, phonetic_blocks


@before_record_insert.connect
@before_record_update.connect
def assign_phonetic_block(sender, *args, **kwargs):
    """Assign phonetic block to each signature.

    The method extends the given signature with a phonetic
    notation of the author's full name, based on
    nysiis algorithm. The phonetic block is assigned before
    the signature is indexed by an Elasticsearch instance.
    """
    authors = sender.get('authors', [])
    authors_map = {}

    for index, author in enumerate(authors):
        if 'full_name' in author:
            authors_map[author['full_name']] = index

    # Use beard to generate phonetic blocks.
    try:
        signatures_blocks = phonetic_blocks(authors_map.keys())
    except Exception as err:
        current_app.logger.error("Cannot extract phonetic blocks for record {0}: {1}", sender.get('control_number'), err)
        return

    # Add signature block to an author.
    for full_name, signature_block in signatures_blocks.iteritems():
        authors[authors_map[full_name]].update(
            {"signature_block": signature_block})


@before_record_insert.connect
@before_record_update.connect
def assign_uuid(sender, *args, **kwargs):
    """Assign uuid to each signature.
    The method assigns to each signature a universally unique
    identifier based on Python's built-in uuid4. The identifier
    is allocated during the insertion of a new record.
    """
    authors = sender.get('authors', [])

    for author in authors:
        # Skip if the author was already populated with a UUID.
        if 'uuid' not in author:
            author['uuid'] = str(uuid.uuid4())


@before_record_index.connect
def generate_name_variations(recid, json, *args, **kwargs):
    """Adds a field with all the possible variations of an authors name.

    :param recid: The id of the record that is going to be indexed.
    :param json: The json representation of the record that is going to be
                 indexed.
    """
    authors = json.get("authors")
    if authors:
        for author in authors:
            name = author.get("full_name")
            if name:
                name_variations = author_tokenize(name)
                author.update({"name_variations": name_variations})
                bai = [
                    item['value'] for item in author.get('ids', [])
                    if item['schema'] == 'INSPIRE BAI'
                ]
                author.update({"name_suggest": {
                    "input": name_variations,
                    "output": name,
                    "payload": {"bai": bai[0] if bai else None}
                }})
