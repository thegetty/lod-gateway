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

from urllib.parse import urljoin

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

    c_uri = urljoin(current_app.config["idPrefix"], container_identifier)
    if not c_uri.endswith("/"):
        c_uri = c_uri + "/"

    container_etag = hash(f"{container_identifier}_{total}")
    etag = hash(f"{container_identifier}_{total}_{current_page}")
    # The Etag will change as the membership total changes and the page.
    headers = {"ETag": etag}

    links = [
        '<http://www.w3.org/ns/ldp#Resource>; rel="type"',
        '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"',
        f'<{c_uri}>; rel="canonical"; etag="{container_etag}"',
        f'<{c_uri}?page=1> rel="first"' f'<{c_uri}?page={pages}> rel="last"',
    ]
    if current_page > 1:
        links.append(f'<{c_uri}?page={current_page - 1}> rel="prev"')
    if current_page < pages:
        links.append(f'<{c_uri}?page={current_page + 1}> rel="next"')

    headers["Link"] = ",".join(links)

    return headers
