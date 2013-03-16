# This file is a part of Fedora Tagger
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301  USA
#
# Refer to the README.rst and LICENSE files for full details of the license
# -*- coding: utf-8 -*-
"""Backend library"""

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.exc import NoResultFound

import model


def create_session(db_url, debug=False, pool_recycle=3600):
    """ Create the Session object to use to query the database.

    :arg db_url: URL used to connect to the database. The URL contains
    information with regards to the database engine, the host to connect
    to, the user and password and the database name.
      ie: <engine>://<user>:<password>@<host>/<dbname>
    :arg debug: a boolean specifying wether we should have the verbose
        output of sqlalchemy or not.
    :return a Session that can be used to query the database.
    """
    engine = create_engine(db_url, echo=debug, pool_recycle=pool_recycle)
    scopedsession = scoped_session(sessionmaker(bind=engine))
    return scopedsession


def add_tag(session, pkgname, tag, ipaddress):
    """ Add a provided tag to the specified package. """
    package = model.Package.by_name(session, pkgname)
    user = model.FASUser.get_or_create(session, ipaddress)
    try:
        tagobj = model.Tag.get(session, package.id, tag)
        tagobj.like += 1
    except NoResultFound:
        tagobj = model.Tag(package_id=package.id, label=tag)
        session.add(tagobj)
        session.flush()
    voteobj = model.Vote(user_id=user.id, tag_id=tagobj.id, like=True)
    session.add(voteobj)
    session.flush()
    return 'Tag "%s" added to the package "%s"' % (tag, pkgname)


def add_rating(session, pkgname, rating, ipaddress):
    """ Add the provided rating to the specified package. """
    package = model.Package.by_name(session, pkgname)
    user = model.FASUser.get_or_create(session, ipaddress)
    ratingobj = model.Rating(package_id=package.id, user_id=user.id,
                             rating=rating)
    session.add(ratingobj)
    session.flush()
    return 'Rating "%s" added to the package "%s"' % (rating, pkgname)


def add_vote(session, pkgname, tag, vote, ipaddress):
    """ Cast a vote for a tag of a specified package. """
    user = model.FASUser.get_or_create(session, ipaddress)
    try:
        package = model.Package.by_name(session, pkgname)
        tagobj = model.Tag.get(session, package.id, tag)
    except SQLAlchemyError, err:
        raise TaggerapiException('This tag could not be found associated'
                                 ' to this package')
    verb = 'changed'
    try:
        # if the vote already exist, replace it
        voteobj = model.Vote.get(session, user_id=user.id,
                                 tag_id=tagobj.id)
        if voteobj.like == vote:
            return 'Your vote on the tag "%s" for the package "%s" did ' \
                   'not changed' % (tag, pkgname)
        else:
            if voteobj.like:
                tagobj.like -= 1
                tagobj.dislike += 1
            else:
                tagobj.dislike -= 1
                tagobj.like += 1
            voteobj.like = vote
    except SQLAlchemyError:
        # otherwise, create it
        verb = 'added'
        voteobj = model.Vote(user_id=user.id, tag_id=tagobj.id, like=vote)
        if vote:
            tagobj.like += 1
        else:
            tagobj.dislike += 1
    session.add(tagobj)
    session.add(voteobj)
    session.flush()
    return 'Vote %s on the tag "%s" of the package "%s"' % (verb, tag, pkgname)


def statistics(session):
    """ Handles the /statistics path.

    Returns an HTML table of statistics on tagged packages.
    """

    packages = model.Package.all(session)
    n_tags = model.Tag.count_unique_label(session)
    raw_data = dict([(p.name, len(p.tags)) for p in packages])

    n_packs = len(raw_data)
    no_tags = len([v for v in raw_data.values() if not v])
    with_tags = n_packs - no_tags

    tags_per_package = 0
    if n_packs:
        tags_per_package = sum([len(p.tags) for p in packages]) \
            / float(n_packs)
    
    tags_per_package_no_zeroes = 0
    if with_tags:
        tags_per_package_no_zeroes = sum([len(p.tags) for p in packages]) \
            / float(with_tags)

    return {
        'summary': {
            'total_packages': n_packs,
            'total_unique_tags': n_tags,
            'no_tags': no_tags,
            'with_tags': with_tags,
            'tags_per_package': tags_per_package,
            'tags_per_package_no_zeroes': tags_per_package_no_zeroes,
        },
    }


class TaggerapiException(Exception):
    """ Generic exception class used to manage exception from taggerapi. """
    pass
