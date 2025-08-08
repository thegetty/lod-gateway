# Container convenience classes, mostly used when creating, searching for, or autogenerating containers

from flask import current_app
from flaskapp.models import db
from flaskapp.models.container import LDPContainer, NoLDPContainerFoundError

from flaskapp.utilities import segment_entity_id


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
