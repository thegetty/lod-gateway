# Container convenience classes, mostly used when creating, searching for, or autogenerating containers

from flask import current_app
from flaskapp.models import db
from flaskapp.models.container import LDPContainer, NoLDPContainerFoundError

from flaskapp.utilities import segment_entity_id


def get_container(container_identifier):
    if current_app.config["LDP_BACKEND"]:
        if (
            result := db.session.query(LDPContainer)
            .filter(LDPContainer.container_identifier == container_identifier)
            .one_or_none()
        ):
            return result
        else:
            raise NoLDPContainerFoundError(container_identifier)
    else:
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
                    if c := get_container(container):
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
