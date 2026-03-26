from __future__ import annotations  # for python 3.10

# Container convenience classes, mostly used when creating, searching for, or autogenerating containers
from uuid import uuid4
from flask import current_app
from flaskapp.models import db
from flaskapp.models.record import Record
from flaskapp.models.container import (
    LDPContainer,
    LDPContainerContents,
    NoLDPContainerFoundError,
)

from flaskapp.utilities import segment_entity_id


def get_container_headers(container_identifier):
    return {
        "Allow": "GET, HEAD, OPTIONS, POST, PATCH",
        "Accept-Post": "application/ld+json",
        "Accept-Patch": "application/ld+json, text/turtle, application/n-quads, application/n-triples",
    }


def create_root_container(dctitle="LOD Gateway", dcdescription=""):
    current_app.logger.info(f"NO ROOT LDP Container found, creating: '{dctitle}'")
    root = LDPContainer(
        container_identifier="/",
        is_root=True,
        dctitle=dctitle,
        dcdescription=dcdescription,
    )
    db.session.add(root)
    db.session.commit()

    return root


def get_container(container_identifier, optimistic=False):
    if current_app.config["LDP_BACKEND"]:
        if (
            result := db.session.query(LDPContainer)
            .filter(LDPContainer.container_identifier == container_identifier)
            .one_or_none()
        ):
            return result
        elif container_identifier == "/":
            # A root should always exist if the LDP Backend is on
            return create_root_container(
                dctitle=current_app.config["AS_DESC"],
                dcdescription="This is the root container for this LOD Service. All containers and "
                "resources hosted by this service will be contained in this root container.",
            )
        else:
            if not optimistic:
                raise NoLDPContainerFoundError(container_identifier)

    return None


def assert_containers(entity_ids):
    # This should only be used to refresh records but not restricted to them
    new_containers = []
    for entity_id in entity_ids:
        current_app.logger.info(f"Refreshing LDP container chain for  '{entity_id}'")
        segments = segment_entity_id(entity_id)
        # Get everything but the root and the last part:
        containers = segments[1:-1]

        # just in case this is a container id instead:
        if segments[-1].endswith("/"):
            containers.append(segments[-1])

        parent = get_container("/")
        for container in containers:
            if c := get_container(container, optimistic=True):
                parent = c
            else:
                # Create inferred container in current transaction
                current_app.logger.info(f"Autogenerating LDP container '{container}'")
                c = LDPContainer(
                    dctitle=container,
                    dcdescription="Auto-generated container",
                    container_identifier=container,
                )
                parent.add_child_container(
                    c, db_dialect=current_app.config["DB_DIALECT"]
                )
                parent = c
                new_containers.append(container)
        try:
            # If it is an existing record, add it to the final container too
            if (
                r := db.session.query(Record)
                .filter(Record.entity_id == entity_id)
                .one_or_none()
            ):
                if r and r.data is not None:
                    parent.add_to_container(
                        r,
                        is_container=False,
                        db_dialect=current_app.config["DB_DIALECT"],
                    )
            db.session.commit()
        except Exception as e:
            current_app.logger.error(
                f"Could not commit new containers for {entity_id} - {str(e)}"
            )
            raise

    return new_containers


def handle_container_requirements(entity_id, entity_type):
    segments = segment_entity_id(entity_id)
    match segments:
        case [_]:
            # handle resource being part of the root container
            return get_container("/")
        case [*containers, _]:
            if not current_app.config["LDP_AUTOCREATE_CONTAINERS"]:
                # only check that final container exists, get it and add the entity id/type optimistically
                if parent := get_container(containers[-1]):
                    return parent
                else:
                    raise NoLDPContainerFoundError(containers[-1])
            else:
                parent = get_container("/")
                for container in containers:
                    if c := get_container(container, optimistic=True):
                        parent = c
                    else:
                        # Create inferred container in current transaction
                        current_app.logger.info(
                            f"Autogenerating LDP container '{container}'"
                        )
                        c = LDPContainer(
                            dctitle=container,
                            dcdescription="Auto-generated container",
                            container_identifier=container,
                        )
                        parent.add_child_container(
                            c, db_dialect=current_app.config["DB_DIALECT"]
                        )
                        parent = c

                # parent should now contain the bottommost container, the parent of the resource
                return parent


def find_parent_container(entity_id, entity_type):
    if (
        c := db.session.query(LDPContainerContents)
        .filter(LDPContainerContents.entity_id == entity_id)
        .filter(LDPContainerContents.entity_type == entity_type)
        .one_or_none()
    ):
        return c.container


def generate_slug_for_container(container_identifier):
    # When RDF resources are POSTed to a container without specifying a Slug
    # It is up to the LDP service to determine a suitable one.

    # TODO Add a feature to get a short id from an ID Manager if enabled
    child_slug = str(uuid4())
    if not current_app.config["LDP_VALIDATE_SLUGS"]:
        return child_slug
    else:
        # As an extra step, make sure that the slug is not already a part of the container
        try:
            if c := get_container(container_identifier):
                entity_id = f"{c.container_identifier}/{child_slug}"
                if c.contents.filter_by(entity_id=entity_id).count() == 0:
                    return child_slug

            # return a failure in all other cases
            return False
        except NoLDPContainerFoundError:
            return False


# Add the current_app base URL for the response base
def get_page_for_container(container_identifier, page=1, page_size=100):
    container = get_container(container_identifier)
    base = f'{current_app.config["idPrefix"]}/'
    return container.paginate_through_content(base, page=page, page_size=page_size)


def generate_paging_link_headers(
    container_identifier, total, current_page, pages, has_next
):
    link_set = paging_navigation_links(
        container_identifier, total, current_page, pages, has_next
    )
    buri = link_set["container"]["base"]
    # The Etag will change as the membership total changes and the page.
    headers = {"ETag": link_set["etag"]}

    # Link headers require FQDN
    links = [
        '<http://www.w3.org/ns/ldp#Resource>; rel="type"',
        '<http://www.w3.org/ns/ldp#Page>; rel="type"',
        f'<{buri}{link_set["this"]}>; rel="this"; etag="{link_set["etag"]}"',
        f'<{link_set["container"]["canonical"]}>; rel="canonical"; etag="{link_set["container"]["etag"]}"',
        f'<{buri}{link_set["first"]}> rel="first"',
        f'<{buri}{link_set["last"]}> rel="last"',
    ]

    if "prev" in link_set:
        links.append(f'<{buri}{link_set["prev"]}> rel="previous"')
    if "next" in link_set:
        links.append(f'<{buri}{link_set["next"]}> rel="next"')

    headers["Link"] = ",".join(links)
    headers["Location"] = f'{buri}{link_set["this"]}'

    return headers


def paging_navigation_links(container_identifier, total, current_page, pages, has_next):
    base_uri = f'{current_app.config["idPrefix"].rstrip("/")}/'
    relative_uri = f"{container_identifier.strip('/')}/"

    container_etag = hash(f"{base_uri}{container_identifier}_{total}")
    etag = hash(f"{base_uri}{container_identifier}_{total}_{current_page}")

    links = {
        "container": {
            "etag": container_etag,
            "canonical": f"{base_uri}{relative_uri}",
            "base": base_uri,
        },
        "etag": etag,
        "first": f"{relative_uri}?page=1",
        "last": f"{relative_uri}?page={pages}",
        "this": f"{relative_uri}?page={current_page}",
    }
    if current_page > 1:
        links["prev"] = f"{relative_uri}?page={current_page - 1}"
    if current_page < pages:
        links["next"] = f"{relative_uri}?page={current_page + 1}"

    return links


def get_full_container_page_representation(cid, page, page_size):
    try:
        # We have a page! return that page of content if possible
        current_app.logger.info(
            f"Attempting to get representation for page {page} of container {cid}"
        )
        pageresp = get_page_for_container(cid, page, page_size)
    except NoLDPContainerFoundError as e:
        # Can't find the container. Pass to record.entity_record? Fail?
        # Going with fail for now:
        current_app.logger.error(
            f"Attempt to retrieve {cid} from database failed {str(e)}"
        )
        raise e

    ldpheaders = generate_paging_link_headers(
        container_identifier=cid,
        total=pageresp["total"],
        current_page=page,
        pages=pageresp["pages"],
        has_next=pageresp["has_next"],
    )

    pagination_uris = paging_navigation_links(
        container_identifier=cid,
        total=pageresp["total"],
        current_page=page,
        pages=pageresp["pages"],
        has_next=pageresp["has_next"],
    )

    data = pageresp["jsonld"]

    data["totalItems"] = pageresp["total"]

    data["dcterms:hasPart"] = {
        "@id": pagination_uris["this"],
        "@type": ["ldp:Resource", "ldp:Page"],
        "first": pagination_uris["first"],
        "last": pagination_uris["last"],
    }

    if "next" in pagination_uris:
        data["dcterms:hasPart"]["next"] = pagination_uris["next"]
    if "prev" in pagination_uris:
        data["dcterms:hasPart"]["prev"] = pagination_uris["prev"]

    return ldpheaders, data
