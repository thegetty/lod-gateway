from flask import Blueprint, render_template, current_app, request, jsonify
from math import ceil
from urllib import parse
from datetime import datetime

from flaskapp.routes.activity_entity import url_base
from flaskapp.models.record import Record
from flaskapp.models.activity import Activity
from sqlalchemy import func, desc, exc
from sqlalchemy.sql.functions import coalesce, max
from flaskapp.models import db

from flaskapp.utilities import wants_html

# Create home page
home_page = Blueprint("home_page", __name__)


@home_page.route("/", methods=["GET"])
@home_page.route("/dashboard", methods=["GET"])
def get_home_page():
    if not wants_html(request):
        return (
            jsonify(
                {
                    "lod_name": current_app.config.get("AS_DESC"),
                    "lod_version": get_version(),
                    "lod_capabilities": current_app.config["SERVER_CAPABILITIES"],
                    "chk_sparql": (
                        True if current_app.config.get("PROCESS_RDF") else False
                    ),
                    "chk_memento": (
                        True if current_app.config.get("KEEP_LAST_VERSION") else False
                    ),
                    "chk_subaddressing": (
                        True if current_app.config.get("SUBADDRESSING") else False
                    ),
                }
            ),
            200,
        )
    # Else, provide the HTML version that requires of all the heavy DB queries
    context = {}
    base_url = url_base()
    items_per_page = (int)(current_app.config["ITEMS_PER_PAGE"])

    # this also covers the case when DB exists but tables not yet created
    # 'total_num_records' is a string - can be 1.4K, 2.3M, etc.
    try:
        total_num_records = get_total_num_records()
    except exc.SQLAlchemyError:
        total_num_records = "0"

    # database is empty, create simplified context
    if total_num_records == "0":
        context = {
            "lod_name": current_app.config.get("AS_DESC"),
            "lod_version": get_version(),
            "num_records": "0",
            "num_changes": "0",
            "as_last_page": 0,
            "chk_sparql": "checked" if current_app.config.get("PROCESS_RDF") else "",
            "chk_memento": (
                "checked" if current_app.config.get("KEEP_LAST_VERSION") else ""
            ),
            "num_entities": 0,
            "chk_subaddressing": (
                "checked" if current_app.config.get("SUBADDRESSING") else ""
            ),
        }
        return render_template("home_page.html", **context)

    # entities
    entities = []
    entity_types = get_distinct_entity_types()

    for entity_type in entity_types:
        ent_obj = get_entity(entity_type, base_url, items_per_page)
        entities.append(ent_obj)

    # link bank
    link_bank = None
    if "LINK_BANK" in current_app.config:
        link_bank = current_app.config["LINK_BANK"]

    # Create context
    context = {
        "lod_name": current_app.config.get("AS_DESC"),
        "lod_version": get_version(),
        "as_last_page": get_total_pages(items_per_page),
        "num_records": total_num_records,
        "num_changes": get_total_num_changes(),
        "chk_sparql": "checked" if current_app.config.get("PROCESS_RDF") else "",
        "chk_memento": "checked" if current_app.config.get("KEEP_LAST_VERSION") else "",
        "chk_subaddressing": (
            "checked" if current_app.config.get("SUBADDRESSING") else ""
        ),
        "last_change": get_last_modified_date(),
        "entities": entities,
        "num_entities": len(entities),
        "link_bank": link_bank,
    }

    return render_template("home_page.html", **context)


# Data access functions ------------------------------------
# Global --------------------
def get_total_pages(items_per_page):
    last = db.session.query(coalesce(max(Activity.id), 0).label("num")).one()

    return ceil(last.num / items_per_page)


def get_total_num_records():
    num_rec = db.session.query(Record).filter(Record.datetime_deleted == None).count()

    return num_rec_to_str(num_rec)


def get_total_num_changes():
    num_rec = db.session.query(Activity).count()

    return num_rec_to_str(num_rec)


def get_last_modified_date():
    # much faster than taking directly max('datetime_created')
    if last_id := Activity.id == db.session.query(func.max(Activity.id)).first():
        if res := (
            db.session.query(Activity.datetime_created)
            .filter(Activity.id == last_id[0])
            .first()
        ):
            return datetime.strftime(res[0], "%m/%d/%y")

    # Empty Activity stream
    return "No activities"


def get_version():
    try:
        with open("version.txt") as f:
            return f.read()
    except OSError:
        return None


# Entities ----------------------------
def get_entity(entity_type, base_url, items_per_page):
    num_changes = get_num_changes_entity(entity_type)
    num_changes_str = num_rec_to_str(num_changes)
    ent_obj = {}
    ent_obj["entity_name"] = entity_type
    ent_obj["num_records"] = num_rec_to_str(get_num_records_entity(entity_type))
    ent_obj["num_changes"] = num_changes_str
    ent_obj["last_updated"] = get_last_modified_date_entity(entity_type)
    total_pages = ceil(num_changes / items_per_page)
    ent_obj["as_last_page"] = str(total_pages)
    rec_id, last_rec, last_date = get_most_recent_changed_record(entity_type)
    ent_obj["most_recent_rec_url"] = f"{base_url}/{last_rec}"
    ent_obj["most_recent_rec"] = last_rec
    ent_obj["most_recent_date"] = datetime.strftime(last_date, "%m/%d/%y")
    ent_obj["most_recent_num_changes"] = get_num_changes_record_entity(rec_id)
    ent_obj["most_recent_as"] = ent_obj["most_recent_rec"] + "/activity-stream"
    ent_obj["num_pages_most_recent_as"] = ceil(
        ent_obj["most_recent_num_changes"] / items_per_page
    )
    ent_obj["most_recent_sparql"] = get_most_recent_sparql(base_url, last_rec)

    return ent_obj


def get_distinct_entity_types():
    # this is much faster than 'distinct'
    result = []
    ent_types = (
        db.session.query(Record.entity_type, func.count(Record.entity_type))
        .filter(Record.datetime_deleted == None)
        .group_by(Record.entity_type)
        .order_by(desc(func.count(Record.entity_type)))
        .all()
    )
    for ent in ent_types:
        if ent and ent[1] > 0:
            result.append(ent[0])

    return result


def get_num_records_entity(entity_type):
    num_rec = (
        db.session.query(Record)
        .filter(Record.entity_type == entity_type)
        .filter(Record.datetime_deleted == None)
        .count()
    )

    return num_rec


def get_num_changes_entity(entity_type):
    num_rec = (
        Activity.query.with_entities(Activity.id)
        .join(Record)
        .filter(Record.entity_type == entity_type)
    ).count()

    return num_rec


def get_last_modified_date_entity(entity_type):
    res = (
        db.session.query(func.max(Activity.datetime_created))
        .join(Record)
        .filter(Record.entity_type == entity_type)
        .first()
    )[0]
    if res is not None:
        return datetime.strftime(res, "%m/%d/%y")


def get_most_recent_changed_record(entity_type):
    res = (
        db.session.query(
            Record.id,
            Record.entity_id,
            Record.datetime_updated,
        )
        .filter(Record.entity_type == entity_type)
        .filter(Record.datetime_deleted == None)
        .order_by(Record.datetime_updated.desc())
        .first()
    )
    if res is not None:
        rec_id = res[0]
        entity_id = res[1]
        last_dt = res[2]

        return (rec_id, entity_id, last_dt)
    else:
        return ("None", "None", "N/A")


def get_num_changes_record_entity(rec_id):
    num_changes = (
        db.session.query(Activity.datetime_created)
        .join(Record)
        .filter(Record.id == rec_id)
        .count()
    )

    return num_changes


def get_most_recent_sparql(base_url, entity_id):
    url = base_url + "/sparql-ui#"
    graph = parse.quote(base_url + "/" + entity_id)
    query1 = parse.quote(
        """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
        SELECT * WHERE {
        graph 
        """
    )

    query2 = parse.quote(
        """
        {
            ?sub ?pred ?obj .
        }
    }
    """
    )

    return f"{url}{query1}{graph}{query2}"


# Helpers ----------------------------
def num_rec_to_str(num_rec):
    num_rec_str = str(num_rec)
    if num_rec > 1_000:
        if num_rec > 1_000_000:
            divider = 1_000_000
            letter = "M"
        else:
            divider = 1_000
            letter = "K"
        num_rec = num_rec / divider
        num_rec = round(num_rec, 1)
        num_rec_str = str(num_rec) + letter

    result = num_rec_str

    return result
