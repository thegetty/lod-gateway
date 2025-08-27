from flaskapp.models import db
from sqlalchemy.sql import func
from sqlalchemy.schema import UniqueConstraint

from flaskapp.utilities import format_datetime

# POSTGRESQL - for the upsert mode
from sqlalchemy.dialects.postgresql import insert as pg_insert


class LDPContainerError(IOError):
    """General purpose class for Container-related exceptions"""


class NoLDPContainerFoundError(LDPContainerError):
    """A Record is being added and the LDPContainer does not exist, or the requested
    LDP Container does not exist"""


class BadContainerSlugError(LDPContainerError):
    """A container cannot be given an slug that containers '/' in its name"""


class LDPContainer(db.Model):
    __tablename__ = "containers"
    id = db.Column(db.Integer, primary_key=True)
    # Bibliographic metadata elements
    dctitle = db.Column(db.String(150), nullable=False)
    dcdescription = db.Column(db.String, nullable=True)
    datetime_created = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # This is the *relative* subpath for this container, not the FQDN
    # no '/' on the end of the string
    container_identifier = db.Column(
        db.String(200), nullable=False, index=True, unique=True
    )

    # Nullable for root nodes (ie direct members of the LOD Gateway 'container')
    # Model also has a boolean 'is_root' to indicate this (which is better than querying on NULL/None)
    is_root = db.Column(db.Boolean, index=True, default=False)
    parent_id = db.Column(
        db.Integer, db.ForeignKey("containers.id"), index=True, nullable=True
    )

    # Relationship to parent and children. dynamic to avoid SQLAlchemy trying to pull a whole hierarchy
    parent = db.relationship(
        "LDPContainer", remote_side=[id], back_populates="children"
    )
    children = db.relationship("LDPContainer", back_populates="parent", lazy="dynamic")

    # One-to-many relationship with LDPContainerContents
    contents = db.relationship(
        "LDPContainerContents", back_populates="container", lazy="dynamic"
    )

    @classmethod
    def get_root_nodes(cls):
        return (
            cls.query.filter_by(is_root=True)
            .order_by(LDPContainer.datetime_created)
            .all()
        )

    @classmethod
    def get_root(cls):
        return (
            cls.query.filter_by(container_identifier="/")
            .order_by(LDPContainer.datetime_created)
            .one_or_none()
        )

    def __repr__(self):
        return f"<LDPContainer id={self.id} path={self.container_identifier} name={self.dctitle}>"

    # Add a child container
    def add_child_container(self, child_container: "LDPContainer", db_dialect="base"):
        child_container.parent = self
        db.session.add(child_container)
        self.add_to_container(child_container, is_container=True, db_dialect=db_dialect)

    # Create a child container
    def new_child_container(
        self, child_slug, dctitle="", dcdescription="", db_dialect="base"
    ):
        if "/" in child_slug:
            raise BadContainerSlugError("The child slug identifier cannot contain '/'")

        container_identifier = f"{self.container_identifier}/{child_slug}"
        if not dctitle:
            dctitle = container_identifier
        child_container = LDPContainer(
            container_identifier=container_identifier,
            dctitle=dctitle,
            dcdescription=dcdescription,
            is_root=False,
        )
        child_container.parent = self
        db.session.add(child_container)
        self.add_to_container(child_container, is_container=True, db_dialect=db_dialect)

    # Add a child Record, but do not flush or commit
    def add_to_container(self, item, is_container: bool = False, db_dialect="base"):
        # Get the right details from the item
        if is_container:
            entity_id = item.container_identifier
            entity_type = "ldp:BasicContainer"
        else:
            entity_id = item.entity_id
            entity_type = item.entity_type

        # Probably shift this test to a flag created once when setting up app.config section eventually
        if db_dialect == "postgresql":
            # The index_elements check might be fine with just entity_id actually. Might be slightly quicker.
            stmt = (
                pg_insert(LDPContainerContents)
                .values(
                    container_id=self.id,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    is_container=is_container,
                )
                .on_conflict_do_nothing(constraint="_container_uniqueness_constraint")
            )
            db.session.execute(stmt)
        else:
            # Fallback for non-PostgreSQL databases
            existing = LDPContainerContents.query.filter_by(
                container_id=self.id, entity_id=entity_id
            ).first()
            if not existing:
                new_entity = LDPContainerContents(
                    container_id=self.id,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    is_container=is_container,
                )
                db.session.add(new_entity)
                return True
            else:
                # Already part of the container - No-Op -> None
                return

    # Remove a child Record, but do not flush or commit
    def remove_from_container(
        self, item, is_container: bool = False, db_dialect="base"
    ):
        # Get the right details from the item
        if is_container:
            entity_id = item.container_identifier
        else:
            entity_id = item.entity_id

        if existing := LDPContainerContents.query.filter_by(
            container_id=self.id, entity_id=entity_id
        ).first():
            db.session.delete(existing)
            return True
        else:
            # Going for the optimistic return rather than a raise Error if it
            # cannot be found in this container
            return False

    def paginate_through_content(self, base, page=1, page_size=100):
        # Paginate through the rows, listing the containers first and then the records,
        # ordered by the
        query = self.contents.order_by(
            db.desc(LDPContainerContents.is_container),  # True first
            LDPContainerContents.id.asc(),
        )

        # Get total (maybe alter the query for speed later if needed? no ordering, just get '1' for each row?)
        # The total will likely part of a hash for the ETag for the container
        total = query.count()

        # Now get the items for the slice we want
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        pages = (total + page_size - 1) // page_size

        container = self.as_jsonld(base)

        # Add the memberlist to the container representation
        container["contains"] = [x.to_ldp() for x in items]

        return {
            "total": total,
            "pages": pages,
            "current_page": page,
            "has_next": page < pages,
            "jsonld": container,
        }

    def as_jsonld(self, base: str):
        # base should be the FQDN for the root container, and should end in '/''
        ci = self.container_identifier
        if ci != "/":
            if not ci.endswith("/"):
                ci = f"{ci}/"
            if ci.startswith("/"):
                # For the relative pathing, with @base
                ci = ci[1:]
        else:
            # Root container IS the base.
            ci = ""
        base_jsonld = {
            "@context": [
                {
                    "ldp": "http://www.w3.org/ns/ldp#",
                    "contains": {"@reverse": "ldp:member"},
                    "dcterm": "http://purl.org/dc/terms/",
                    "@base": base,
                },
            ],
            "@id": ci,
            "dcterm:title": self.dctitle,
            "@type": ["ldp:BasicContainer", "ldp:Container"],
        }
        if self.dcdescription:
            base_jsonld["dcterm:description"] = self.dcdescription

        return base_jsonld


class LDPContainerContents(db.Model):
    __tablename__ = "entity_list"

    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.String(250), nullable=False, unique=True, index=True)
    # NB ldp_BasicLDPContainer will also be present here, for completeness. This should reflect
    entity_type = db.Column(db.String(70), nullable=False)
    # to make child container retrieval and ordering quicker, because it is expected that there will
    # be very many more is_container=False rows than True
    # (NB if it was 50:50 True/False, it won't be optimal and may even slow things down to include this index #theMoreYouKnow)
    is_container = db.Column(db.Boolean, index=True, default=False)
    date_added = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # Has to be part of a LDPContainer
    container_id = db.Column(
        db.Integer, db.ForeignKey("containers.id"), nullable=False, index=True
    )
    container = db.relationship("LDPContainer", back_populates="contents")

    # Set up link uniqueness constraint here
    __table_args__ = (
        UniqueConstraint(
            "container_id",
            "entity_id",
            name="_container_uniqueness_constraint",
        ),
    )

    def __repr__(self):
        return f"<LDPContainerContents id={self.id} entity_id={self.entity_id} type={self.entity_type}>"

    def to_dict(self):
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "is_container": self.is_container,
            "date_added": self.date_added,
        }

    def to_ldp(self):
        entid = self.entity_id
        if entid.startswith("/"):
            # For the relative ids using @base
            entid = entid[1:]
        return {
            "@id": entid,
            "dcterm:type": self.entity_type,
            "dcterm:available": format_datetime(self.date_added),
        }
