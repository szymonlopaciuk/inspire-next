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

import json

import pytest
from flask import current_app, session

from flask_security import current_user
from flask_security.utils import hash_password

from invenio_access.models import ActionRoles, ActionUsers
from invenio_accounts.models import Role, SessionActivity, User
from invenio_accounts.testutils import (
    login_user_via_session,
    login_user_via_view,
)
from invenio_cache import current_cache
from invenio_collections.models import Collection
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier
from invenio_search import current_search_client as es

from inspirehep.modules.pidstore.minters import inspire_recid_minter
from inspirehep.modules.records.api import InspireRecord
from inspirehep.modules.records.permissions import load_user_collections
from inspirehep.modules.search.api import LiteratureSearch


def _create_and_index_record(record):
    record = InspireRecord.create(record)
    inspire_recid_minter(record.id, record)
    db.session.commit()
    es.indices.refresh('records-hep')

    return record


@pytest.fixture(scope='function')
def sample_record(app):
    record = {
        '$schema': 'http://localhost:5000/schemas/records/hep.json',
        '_collections': [
            'Literature',
        ],
        'control_number': 111,
        'document_type': [
            'article',
        ],
        'titles': [
            {'title': 'sample'}
        ],
    }
    record = _create_and_index_record(record)
    record_id = record.id

    yield record

    pid = PersistentIdentifier.get('lit', '111')
    db.session.delete(pid)
    record = InspireRecord.get_record(record_id)
    record._delete(force=True)
    current_app.extensions[
        'invenio-db'].versioning_manager.transaction_cls.query.delete()
    db.session.commit()


@pytest.fixture(scope='function')
def restricted_record(app):
    restricted_collection = Collection(
        name='Restricted Collection',
        dbquery='_collections:"Restricted Collection"',
    )
    another_restricted_collection = Collection(
        name='Another Restricted Collection',
        dbquery='_collections:"Another Restricted Collection"',
    )

    db.session.add_all([restricted_collection, another_restricted_collection])
    db.session.commit()

    record = {
        '$schema': 'http://localhost:5000/schemas/records/hep.json',
        '_collections': [
            'Literature',
            'Restricted Collection',
            'Another Restricted Collection',
        ],
        'control_number': 222,
        'document_type': [
            'article',
        ],
        'titles': [
            {'title': 'restricted'}
        ],
    }

    record = _create_and_index_record(record)
    yield record

    collection = Collection.query.filter_by(
        name='Restricted Collection'
    ).one()
    another_collection = Collection.query.filter_by(
        name='Another Restricted Collection'
    ).one()
    pid = PersistentIdentifier.get('lit', '222')
    db.session.delete(collection)
    db.session.delete(another_collection)
    db.session.delete(pid)
    record._delete(force=True)
    current_app.extensions[
        'invenio-db'].versioning_manager.transaction_cls.query.delete()
    db.session.commit()
    current_cache.delete('restricted_collections')


@pytest.fixture(scope='function')
def users(app):
    # Create test users
    hashed_password = hash_password('123456')
    user = User(
        email='user@inspirehep.net',
        password=hashed_password,
        active=True
    )
    user_partially_allowed = User(
        email='partially_allowed@inspirehep.net',
        password=hashed_password,
        active=True,
    )
    user_allowed = User(
        email='allowed@inspirehep.net',
        password=hashed_password,
        active=True,
    )

    collection_restricted_role = Role(
        name='restrictedcollmaintainer'
    )

    user_allowed_with_role = User(
        email='allowedrole@inspirehep.net',
        password=hashed_password,
        active=True,
        roles=[collection_restricted_role]
    )

    db.session.add_all(
        [
            user, user_partially_allowed, user_allowed,
            user_allowed_with_role, collection_restricted_role
        ]
    )
    db.session.commit()

    # Create actions for the allowed user
    restricted_collection_action = ActionUsers(
        action='view-restricted-collection',
        argument='Restricted Collection',
        user_id=user_allowed.id
    )
    another_restricted_collection_action = ActionUsers(
        action='view-restricted-collection',
        argument='Another Restricted Collection',
        user_id=user_allowed.id
    )

    # Create actions for the partially allowed user
    partial_restricted_collection_action = ActionUsers(
        action='view-restricted-collection',
        argument='Restricted Collection',
        user_id=user_partially_allowed.id
    )

    # Create actions for the allowed role
    partial_restricted_collection_role_action = ActionRoles(
        action='view-restricted-collection',
        argument='Restricted Collection',
        role_id=collection_restricted_role.id
    )

    role_only_collection_action = ActionRoles(
        action='view-restricted-collection',
        argument='Role only collection',
        role_id=collection_restricted_role.id
    )

    db.session.add_all(
        [
            restricted_collection_action,
            another_restricted_collection_action,
            partial_restricted_collection_action,
            partial_restricted_collection_role_action,
            role_only_collection_action
        ]
    )
    db.session.commit()

    yield

    current_cache.clear()
    SessionActivity.query.delete()
    ActionRoles.query.filter_by(action='view-restricted-collection').delete()
    ActionUsers.query.filter_by(action='view-restricted-collection').delete()
    User.query.filter_by(email='user@inspirehep.net').delete()
    User.query.filter_by(email='partially_allowed@inspirehep.net').delete()
    User.query.filter_by(email='allowed@inspirehep.net').delete()
    db.session.delete(Role.query.filter_by(name='restrictedcollmaintainer').one())
    db.session.delete(User.query.filter_by(email='allowedrole@inspirehep.net').one())
    db.session.commit()


@pytest.mark.usefixtures("users", "sample_record")
def test_all_collections_are_cached(app, app_client):
    """Test that collection info gets cached."""

    # Remove collection cache key
    current_cache.delete('restricted_collections')

    app_client.get("/literature/111")

    # Check that cache key has been correctly filled
    assert current_cache.get('restricted_collections') == \
        set([u'Another Restricted Collection', u'Restricted Collection', u'Role only collection'])


@pytest.mark.parametrize('user_info,status', [
    # anonymous user
    (None, 200),
    # Logged in user without permissions assigned
    (dict(email='user@inspirehep.net'), 200),
    # Logged in user with permissions assigned
    (dict(email='allowed@inspirehep.net'), 200),
    # admin user
    (dict(email='admin@inspirehep.net'), 200),
])
@pytest.mark.usefixtures("users", "sample_record")
def test_record_public_detailed_read(app, app_client, user_info, status):
    """Test that a record can be read by everybody through web interface."""
    if user_info:
        # Login as user
        login_user_via_session(app_client, email=user_info['email'])

    assert app_client.get('/literature/111').status_code == status


@pytest.mark.parametrize('user_info,status', [
    # anonymous user
    (None, 200),
    # Logged in user without permissions assigned
    (dict(email='user@inspirehep.net'), 200),
    # Logged in user with permissions assigned
    (dict(email='allowed@inspirehep.net'), 200),
    # admin user
    (dict(email='admin@inspirehep.net'), 200),
])
@pytest.mark.usefixtures("users", "sample_record")
def test_record_public_api_read(app, app_client, user_info, status):
    """Test that a record can be read by everybody through the API."""
    if user_info:
        # Login as user
        login_user_via_session(app_client, email=user_info['email'])

    assert app_client.get('/literature/111').status_code == status


@pytest.mark.parametrize('user_info,status', [
    # anonymous user
    (None, 302),
    # Logged in user without permissions assigned
    (dict(email='user@inspirehep.net'), 403),
    # Logged in user not allowed in all collections
    (dict(email='partially_allowed@inspirehep.net'), 403),
    (dict(email='allowedrole@inspirehep.net'), 403),
    # Logged in user with permissions assigned
    (dict(email='allowed@inspirehep.net'), 200),
    # admin user
    (dict(email='admin@inspirehep.net'), 200),
])
@pytest.mark.usefixtures("users", "restricted_record")
def test_record_restricted_detailed_read(app, app_client, user_info, status):
    """Test permissions of restricted record accessing detailed view."""

    if user_info:
        # Login as user
        login_user_via_session(app_client, email=user_info['email'])

    assert app_client.get('/literature/222').status_code == status


@pytest.mark.parametrize('user_info,status', [
    # anonymous user
    (None, 401),
    # Logged in user without permissions assigned
    (dict(email='user@inspirehep.net'), 403),
    # Logged in user not allowed in all collections
    (dict(email='partially_allowed@inspirehep.net'), 403),
    # Logged in user with permissions assigned
    (dict(email='allowed@inspirehep.net'), 200),
    # admin user
    (dict(email='admin@inspirehep.net'), 200),
])
@pytest.mark.usefixtures("users", "restricted_record")
def test_record_restricted_api_read(app, api_client, user_info, status):
    """Test permissions of a restricted record through the API."""

    if user_info:
        login_user_via_session(api_client, email=user_info['email'])
    assert api_client.get('/literature/222').status_code == status


@pytest.mark.parametrize('user_info,total_count,es_filter', [
    # anonymous user
    (None, 23, [{'bool': {'must_not': [{'match': {'_collections': u'Another Restricted Collection'}}, {'match': {'_collections': u'Restricted Collection'}}, {'match': {'_collections': u'Role only collection'}}], 'must': [{'match': {'_collections': 'Literature'}}]}}]),
    # Logged in user without permissions assigned
    (dict(email='user@inspirehep.net', password='123456'), 23, [{'bool': {'must_not': [{'match': {'_collections': u'Another Restricted Collection'}}, {'match': {'_collections': u'Restricted Collection'}}, {'match': {'_collections': u'Role only collection'}}], 'must': [{'match': {'_collections': 'Literature'}}]}}]),
    # Logged in user not allowed in all collections
    (dict(email='partially_allowed@inspirehep.net', password='123456'), 23, [{'bool': {'must_not': [{'match': {'_collections': u'Another Restricted Collection'}}, {'match': {'_collections': u'Role only collection'}}], 'must': [{'match': {'_collections': 'Literature'}}]}}]),
    (dict(email='allowedrole@inspirehep.net', password='123456'), 23, [{'bool': {'must_not': [{'match': {'_collections': u'Another Restricted Collection'}}], 'must': [{'match': {'_collections': 'Literature'}}]}}]),
    # Logged in user with permissions assigned
    (dict(email='allowed@inspirehep.net', password='123456'), 24, [{'bool': {'must_not': [{'match': {'_collections': u'Role only collection'}}], 'must': [{'match': {'_collections': 'Literature'}}]}}]),
    # admin user
    (dict(email='admin@inspirehep.net', password='123456'), 24, [{'match': {'_collections': 'Literature'}}]),
])
@pytest.mark.usefixtures("users", "restricted_record")
def test_inspire_search_filter(app, app_client, user_info, total_count, es_filter):
    """Test default inspire search filter."""

    if user_info:
        login_user_via_view(app_client, email=user_info['email'],
                            password=user_info['password'],
                            login_url='/login/?local=1')

    # Doing a client request creates a request context that allows the
    # assert to correctly use the logged in user.
    app_client.get('/search')
    assert LiteratureSearch().to_dict()['query']['bool'][
        'filter'] == es_filter
    assert LiteratureSearch().count() == total_count


@pytest.mark.parametrize('user_info,status', [
    # anonymous user
    (None, 401),
    # Logged in user without permissions assigned
    (dict(email='user@inspirehep.net'), 403),
    # admin user
    (dict(email='admin@inspirehep.net'), 200),
    # Logged in user with permissions assigned
    (dict(email='cataloger@inspirehep.net'), 200)
])
@pytest.mark.usefixtures("users")
def test_record_api_update(app, api_client, sample_record, user_info, status):
    """Test that a record can be updated only from admin
       and cataloger users through the API."""
    if user_info:
        login_user_via_session(api_client, email=user_info['email'])
    resp = api_client.put('/literature/111/db',
                          data=json.dumps(sample_record.dumps()),
                          content_type='application/json')
    assert resp.status_code == status


@pytest.mark.parametrize('user_info,collections', [
    (None, set()),
    (dict(email='partially_allowed@inspirehep.net'), set([u'Restricted Collection'])),
    (dict(email='allowed@inspirehep.net'), set([u'Restricted Collection', u'Another Restricted Collection'])),
    (dict(email='allowedrole@inspirehep.net'), set([u'Restricted Collection', u'Role only collection']))
])
@pytest.mark.usefixtures("users")
def test_load_user_collections(app_client, user_info, collections):
    if user_info:
        login_user_via_session(app_client, email=user_info['email'])
    with app_client.get('/'):
        load_user_collections(current_app, current_user)
        assert session['restricted_collections'] == collections


def test_load_user_collections_called_upon_login(app_client, users):
    login_user_via_view(
        app_client, email='allowed@inspirehep.net',
        password='123456', login_url='/login/?local=1'
    )
    with app_client.get('/'):
        assert session['restricted_collections']
